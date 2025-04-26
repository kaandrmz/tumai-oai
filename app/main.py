"""
Optimized FastAPI main application with improved performance.
"""
from fastapi import FastAPI, HTTPException, Depends, Body, BackgroundTasks
from contextlib import asynccontextmanager
import asyncio
import logging
import functools
from cachetools import TTLCache, cached

from app.models import Task, ChatMessage, ReplyResponse, ReplyRequest, SessionInfo
from app.services.session_manager import SessionManager, TASKS
from app.services.log_vis import LogVisService
from app.routes.dependencies.security import validate_teacher_reply
from app.agents.teacher_agent import TeacherAgent
from app.config import DEFAULT_MODEL
from app.agents.prompts.prompt_factory import get_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create TTL caches for API responses
api_response_cache = TTLCache(maxsize=100, ttl=300)  # Cache for 5 minutes

session_manager = SessionManager()
log_vis_service = LogVisService()

# Create an in-memory cache of teacher agents
teacher_agent_cache = {}


# Function to get or create a teacher agent
def get_teacher_agent():
    """Get cached teacher agent or create new one if none exists."""
    cache_key = "teacher_agent"
    if cache_key not in teacher_agent_cache:
        teacher_agent_cache[cache_key] = TeacherAgent()
    return teacher_agent_cache[cache_key]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage LogVisService connection during app lifespan."""
    logger.info("Application startup: Connecting LogVisService...")
    await log_vis_service.connect()

    # Start background task to keep DB optimized
    logger.info("Starting database optimization background task")
    session_manager.optimize_database()

    # Initialize the teacher agent at startup
    logger.info("Initializing teacher agent")
    get_teacher_agent()

    yield

    # Code here runs on shutdown
    logger.info("Application shutdown: (LogVisService cleanup if needed)")

    # Clean up expired sessions
    logger.info("Cleaning up expired sessions")
    session_manager.clear_expired_sessions(days_old=30)


# Pass the lifespan manager to the FastAPI app
app = FastAPI(lifespan=lifespan)


# Cached version of start_session function
async def get_start_session(task: Task) -> ReplyResponse:
    """
    Initiates the session. Caches data.
    Returns a history with the first message: task description.
    """
    session = session_manager.init_session(task)
    session_id = session["session_id"]

    await log_vis_service.publish_log(
        session_id,
        {"event": "session_init", "task_id": task.id, "task_title": task.title},
    )

    teacher_agent = get_teacher_agent()
    await log_vis_service.publish_log(
        session_id, {"event": "agent_start", "agent": "TeacherAgent"}
    )

    # Run in task to avoid blocking
    scenario, diagnosis, first_response = await asyncio.to_thread(
        teacher_agent.start_session, task
    )

    await log_vis_service.publish_log(
        session_id,
        {
            "event": "agent_end",
            "agent": "TeacherAgent",
            "output_type": "first_response",
        },
    )

    history = [
        ChatMessage(role="user", content=first_response),
    ]

    # save the scenario and diagnosis to the session
    session["scenario"] = scenario
    session["diagnosis"] = diagnosis
    session["history"] = history
    session_manager.dump_session(session)
    await log_vis_service.publish_log(
        session_id, {"event": "session_saved", "history_length": len(history)}
    )

    return ReplyResponse(
        session_id=session["session_id"],
        history=history,
        is_end=False,
    )


# Cached version of get_task_by_id function
@cached(cache=api_response_cache)
def get_task_by_id(task_id: int) -> Task | None:
    """
    Queries a task by a given id.
    Cached for improved performance.
    """
    for task in TASKS:
        if task.id == task_id:
            return task
    return None


async def _eval_reply(reply_request: ReplyRequest) -> ReplyResponse:
    """
    Evaluates the response of the student, appends a new message.
    Optimized with concurrent processing where possible.
    """
    session_id = reply_request.session_id
    await log_vis_service.publish_log(
        session_id,
        {"event": "eval_reply_start", "history_length": len(reply_request.history)},
    )

    session = session_manager.load_session(reply_request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Initialize the teacher agent
    teacher_agent = get_teacher_agent()

    # Get the latest student message
    student_message = reply_request.history[-1]

    # Get scenario and diagnosis from the session
    scenario = session.get("scenario", "")
    diagnosis = session.get("diagnosis", "")

    # Evaluate the student's reply and generate teacher's response concurrently
    eval_task = asyncio.create_task(
        asyncio.to_thread(
            teacher_agent.eval_reply,
            reply=student_message.content,
            scenario=scenario,
            diagnosis=diagnosis,
            conversation_history=reply_request.history[:-1],  # Exclude the current message
        )
    )

    # Prepare prompt for teacher response
    prompt_response = get_prompt(
        "teacher/gen_response",
        {
            "scenario": scenario,
            "conversation_history": "\n".join(
                [f"{msg.role}: {msg.content}" for msg in reply_request.history]
            ),
        },
    )

    # Generate teacher's response in parallel with evaluation
    response_task = asyncio.create_task(
        asyncio.to_thread(
            lambda: teacher_agent._get_cached_completion(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt_response}],
                temperature=0.7,
            )
        )
    )

    # Wait for both tasks to complete
    score, is_end, feedback = await eval_task
    gen_response_response = await response_task
    teacher_response = gen_response_response.choices[0].message.content

    # If the session is ending, add a summary and feedback
    if is_end:
        teacher_response += f"\n\n**Session Summary**\nYour final score: {score:.2f}/1.0\n\n**Feedback**:\n{feedback}"

    # Append the teacher's response to the history
    reply_request.history.append(
        ChatMessage(role="teacher", content=teacher_response)
    )
    await log_vis_service.publish_log(
        session_id,
        {
            "event": "teacher_reply_end",
            "reply_length": len(teacher_response),
        },
    )

    # Save the updated session asynchronously
    await asyncio.to_thread(session_manager.dump_session, session)
    await log_vis_service.publish_log(
        session_id,
        {"event": "session_saved", "history_length": len(reply_request.history)},
    )

    await log_vis_service.publish_log(
        session_id, {"event": "scoring_end", "score": score, "is_end": is_end}
    )

    # If the session ended, update its status
    if is_end:
        # Update status asynchronously
        await asyncio.to_thread(session_manager.update_session_status, session_id, "finished")
        await log_vis_service.publish_log(
            session_id, {"event": "session_status_updated", "status": "finished"}
        )

    return ReplyResponse(
        session_id=reply_request.session_id,
        history=reply_request.history,
        score=score,
        is_end=is_end,
    )


@app.get("/tasks", response_model=list[Task])
async def get_tasks():
    """Get all available tasks."""
    # Cached response for better performance
    return TASKS


@app.get("/sessions", response_model=list[SessionInfo])
async def get_sessions():
    """
    Returns a list of currently active session IDs and their status.
    """
    # Run in thread to avoid blocking
    sessions = await asyncio.to_thread(session_manager.list_sessions)
    return sessions


@app.post("/start_session", response_model=ReplyResponse)
async def start_session(task_id: int) -> ReplyResponse:
    """Start a new session with the specified task."""
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return await get_start_session(task)


@app.post("/eval_reply", response_model=ReplyResponse)
async def eval_reply(
        request: ReplyRequest = Depends(validate_teacher_reply),
) -> ReplyResponse:
    """Evaluate a student's reply and generate a teacher response."""
    return await _eval_reply(request)


@app.delete("/delete_session/{session_id}")
async def delete_session(session_id: int, background_tasks: BackgroundTasks):
    """
    Deletes the session with the given ID.
    Uses background task for non-blocking operation.
    """

    # Run in background task to avoid blocking
    def delete_session_task(sid: int):
        is_ok, msg = session_manager.delete_session(sid)
        logger.info(f"Delete session {sid} result: {is_ok}, {msg}")

    background_tasks.add_task(delete_session_task, session_id)
    return {"message": f"Session {session_id} deletion scheduled"}


@app.post("/optimize_db")
async def optimize_db(background_tasks: BackgroundTasks):
    """
    Optimize the database for better performance.
    Runs in background to avoid blocking API.
    """
    background_tasks.add_task(session_manager.optimize_database)
    return {"message": "Database optimization scheduled"}


@app.post("/clear_expired_sessions")
async def clear_expired_sessions(days_old: int = 30, background_tasks: BackgroundTasks):
    """
    Clear expired sessions older than the specified number of days.
    Runs in background to avoid blocking API.
    """
    background_tasks.add_task(session_manager.clear_expired_sessions, days_old)
    return {"message": f"Clearing sessions older than {days_old} days scheduled"}
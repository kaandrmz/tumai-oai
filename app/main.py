from fastapi import FastAPI, HTTPException, Depends, Body
from contextlib import asynccontextmanager
from app.models import Task, ChatMessage, ReplyResponse, ReplyRequest, SessionInfo
from app.services.session_manager import SessionManager, TASKS
from app.services.log_vis import LogVisService
from app.routes.dependencies.security import validate_teacher_reply
from app.agents.teacher_agent import TeacherAgent
from app.config import DEFAULT_MODEL
from app.agents.prompts.prompt_factory import get_prompt

app = FastAPI()
session_manager = SessionManager()
log_vis_service = LogVisService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage LogVisService connection during app lifespan."""
    print("Application startup: Connecting LogVisService...")
    await log_vis_service.connect()

    # Initialize the teacher agent at startup
    yield
    print("Application shutdown: Disconnecting LogVisService...")
    await log_vis_service.disconnect()


# Pass the lifespan manager to the FastAPI app
app = FastAPI(lifespan=lifespan)


async def get_start_session(task: Task) -> ReplyResponse:
    """
    Initiates the session. Caches data.
    Returns a history with the first message: task decription.
    """
    session = session_manager.init_session(task)
    session_id = session["session_id"]

    await log_vis_service.publish_log(
        session_id,
        {"event": "session_init", "task_id": task.id, "task_title": task.title},
    )

    teacher_agent = TeacherAgent()
    await log_vis_service.publish_log(
        session_id, {"event": "agent_start", "agent": "TeacherAgent", "method": "start_session"}
    )

    scenario, diagnosis, first_response = teacher_agent.start_session(task)
    await log_vis_service.publish_log(
        session_id,
        {
            "event": "agent_end",
            "agent": "TeacherAgent",
            "method": "start_session",
            "output_type": "scenario_diagnosis_response",
            "diagnosis_preview": diagnosis[:100] + "..." if diagnosis else "N/A"
        },
    )

    history = [
        ChatMessage(role="teacher", content=first_response),
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


def get_task_by_id(task_id: int) -> Task | None:
    """
    Queries a task by a given id.
    """
    for task in TASKS:
        if task.id == task_id:
            return task
    return None


async def _eval_reply(reply_request: ReplyRequest) -> ReplyResponse:
    """
    Evaluates the response of the student, appends a new message.
    """
    session_id = reply_request.session_id
    await log_vis_service.publish_log(
        session_id,
        {"event": "eval_reply_start", "history_length": len(reply_request.history)},
    )
    
    # Log the incoming student message
    student_message = reply_request.history[-1]
    if student_message.role == 'user': # Assuming student role is 'user'
        await log_vis_service.publish_log(
            session_id,
            {"event": "chat_message", "role": student_message.role, "content": student_message.content}
        )

    session = session_manager.load_session(reply_request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Initialize the teacher agent
    teacher_agent = TeacherAgent()

    # Get the latest student message
    student_message = reply_request.history[-1]

    # Get scenario and diagnosis from the session
    scenario = session.get("scenario", "")
    diagnosis = session.get("diagnosis", "")

    # Evaluate the student's reply
    score, is_end, feedback = teacher_agent.eval_reply(
        reply=student_message.content,
        scenario=scenario,
        diagnosis=diagnosis,
        conversation_history=reply_request.history[:-1],  # Exclude the current message
    )
    await log_vis_service.publish_log(
        session_id,
        {
            "event": "agent_end",
            "agent": "TeacherAgent",
            "method": "eval_reply",
            "score": score,
            "is_end": is_end,
            "feedback_preview": feedback[:100] + "..." if feedback else "N/A"
        },
    )

    # Generate teacher's response based on evaluation
    prompt_response = get_prompt(
        "teacher/gen_response",
        {
            "scenario": scenario,
            "conversation_history": "\n".join(
                [f"{msg.role}: {msg.content}" for msg in reply_request.history]
            ),
        },
    )

    gen_response_response = teacher_agent.openai_client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt_response}],
        temperature=0.7,
    )

    teacher_response = gen_response_response.choices[0].message.content
    await log_vis_service.publish_log(
        session_id, {"event": "openai_call_end", "response_length": len(teacher_response or "")}
    )

    if is_end:
        teacher_response += f"\n\n**Session Summary**\nYour final score: {score:.2f}/1.0\n\n**Feedback**:\n{feedback}"
        await log_vis_service.publish_log(
            session_id, {"event": "feedback_added_to_response"}
        )

    # Log the outgoing teacher message BEFORE appending to history sent back
    if teacher_response:
        await log_vis_service.publish_log(
            session_id,
            {"event": "chat_message", "role": "teacher", "content": teacher_response}
        )
        
    reply_request.history.append(
        ChatMessage(role="teacher", content=teacher_response)
    )

    session_manager.dump_session(session)
    await log_vis_service.publish_log(
        session_id,
        {"event": "session_saved", "history_length": len(reply_request.history)},
    )

    # TODO@zeynepyorulmaz: implement scoring and end conditions
    score, is_end = 0.8, False
    await log_vis_service.publish_log(
        session_id, {"event": "scoring_end", "score": score, "is_end": is_end}
    )

    # If the session ended, update its status
    if is_end:
        session_manager.update_session_status(session_id, "finished")
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
def get_tasks():
    return TASKS


@app.get("/sessions", response_model=list[SessionInfo])
def get_sessions():
    """
    Returns a list of currently active session IDs and their status.
    """
    sessions = session_manager.list_sessions()
    return sessions


@app.post("/start_session", response_model=ReplyResponse)
async def start_session(task_id: int) -> ReplyResponse:
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return await get_start_session(task)


@app.post("/eval_reply", response_model=ReplyResponse)
async def eval_reply(
    request: ReplyRequest = Depends(validate_teacher_reply),
) -> ReplyResponse:
    return await _eval_reply(request)


@app.delete("/delete_session/{session_id}")
async def delete_session(session_id: int):
    """
    Deletes the session with the given ID.
    """
    sm = SessionManager()
    is_ok, msg = sm.delete_session(session_id)
    return {"success": is_ok, "message": msg}

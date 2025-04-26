from fastapi import FastAPI, HTTPException, Depends, Body
from contextlib import asynccontextmanager
from app.models import Task, ChatMessage, ReplyResponse, ReplyRequest, SessionInfo
from app.services.session_manager import SessionManager, TASKS
from app.services.log_vis import LogVisService
from app.routes.dependencies.security import validate_teacher_reply
from app.agents.teacher_agent import TeacherAgent

session_manager = SessionManager()
log_vis_service = LogVisService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage LogVisService connection during app lifespan."""
    print("Application startup: Connecting LogVisService...")
    await log_vis_service.connect()
    # TODO: Consider adding a disconnect method to LogVisService and call it here on shutdown
    yield
    # Code here runs on shutdown
    print("Application shutdown: (LogVisService cleanup if needed)")

# Pass the lifespan manager to the FastAPI app
app = FastAPI(lifespan=lifespan)

async def get_start_session(task: Task) -> ReplyResponse:
    """
    Initiates the session. Caches data.
    Returns a history with the first message: task decription.
    """
    session = session_manager.init_session(task)
    session_id = session["session_id"]

    await log_vis_service.publish_log(session_id, {"event": "session_init", "task_id": task.id, "task_title": task.title})

    teacher_agent = TeacherAgent()
    await log_vis_service.publish_log(session_id, {"event": "agent_start", "agent": "TeacherAgent"})
    scenario, first_response = teacher_agent.start_session(task)
    await log_vis_service.publish_log(session_id, {"event": "agent_end", "agent": "TeacherAgent", "output_type": "first_response"})
    history = [
        ChatMessage(role="user", content=first_response),
    ]

    # save the scenario to the session
    session["scenario"] = scenario
    session["history"] = history
    session_manager.dump_session(session)
    await log_vis_service.publish_log(session_id, {"event": "session_saved", "history_length": len(history)})

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
    await log_vis_service.publish_log(session_id, {"event": "eval_reply_start", "history_length": len(reply_request.history)})

    session = session_manager.load_session(reply_request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    await log_vis_service.publish_log(session_id, {"event": "teacher_reply_start"})
    # Simulate teacher thinking/processing
    reply_request.history.append(
        ChatMessage(role="teacher", content="A sample reply from the teacher.")
    )
    await log_vis_service.publish_log(session_id, {"event": "teacher_reply_end", "reply_length": len("A sample reply from the teacher.")})

    session["history"] = [msg.model_dump() for msg in reply_request.history] # Update session with new history
    session_manager.dump_session(session)
    await log_vis_service.publish_log(session_id, {"event": "session_saved", "history_length": len(reply_request.history)})

    # TODO@zeynepyorulmaz: implement scoring and end conditions
    await log_vis_service.publish_log(session_id, {"event": "scoring_start"})
    score, is_end = 0.8, False # Replace with actual logic
    await log_vis_service.publish_log(session_id, {"event": "scoring_end", "score": score, "is_end": is_end})

    # If the session ended, update its status
    if is_end:
        session_manager.update_session_status(session_id, "finished")
        await log_vis_service.publish_log(session_id, {"event": "session_status_updated", "status": "finished"})
    
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

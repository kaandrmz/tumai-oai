from fastapi import FastAPI, HTTPException, Depends, Body
from app.models import Task, ChatMessage, ReplyResponse, ReplyRequest
from app.services.session_manager import SessionManager, TASKS
from app.services.log_vis import LogVisService
from app.routes.dependencies.security import validate_teacher_reply
from app.agents.teacher_agent import TeacherAgent
app = FastAPI()
session_manager = SessionManager()
log_vis_service = LogVisService()

def get_start_session(task: Task) -> ReplyResponse:
    """
    Initiates the session. Caches data.
    Returns a history with the first message: task decription.
    """
    session = session_manager.init_session(task)

    teacher_agent = TeacherAgent()
    scenario, first_response = teacher_agent.start_session(task)
    history = [
        ChatMessage(role="user", content=scenario),
    ]

    # save the scenario to the session
    session["scenario"] = scenario
    session["history"] = history
    session_manager.dump_session(session)
    
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


def _eval_reply(reply_request: ReplyRequest) -> ReplyResponse:
    """
    Evaluates the response of the student, appends a new message.
    """
    session = session_manager.load_session(reply_request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    reply_request.history.append(
        ChatMessage(role="teacher", content="A sample reply from the teacher.")
    )

    session.history = reply_request.history
    session_manager.dump_session(session)

    return ReplyResponse(scenario=session, score=0.9, is_end=False)


@app.get("/tasks", response_model=list[Task])
def get_tasks():
    return TASKS


@app.post("/start_session", response_model=ReplyResponse)
def start_session(task_id: int) -> ReplyResponse:
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return get_start_session(task)


@app.post("/eval_reply", response_model=ReplyResponse)
def eval_reply(
    request: ReplyRequest = Depends(validate_teacher_reply),
) -> ReplyResponse:
    return _eval_reply(request)

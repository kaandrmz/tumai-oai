from fastapi import FastAPI, HTTPException
from app.models import Task, ChatMessage, ScoreFeedback, Scenario, ReplyRequest
from app.services.session_manager import SessionManager, TASKS
from app.services.log_vis import LogVisService

app = FastAPI()
session_manager = SessionManager()
log_vis_service = LogVisService()

def get_start_session(task: Task) -> Scenario:
    """
    Initiates the session. Caches data.
    Returns a history with the first message: task decription.
    """
    return session_manager.init_session(task)


def get_task_by_id(task_id: int) -> Task | None:
    """
    Queries a task by a given id.
    """
    for task in TASKS:
        if task.id == task_id:
            return task
    return None


def _eval_reply(reply_request: ReplyRequest) -> ScoreFeedback:
    """
    Evaluates the response of the student, appends a new message.
    """
    scenario = session_manager.load_session(reply_request.session_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Session not found.")

    reply_request.history.append(
        ChatMessage(role="teacher", content="A sample reply from the teacher.")
    )

    scenario.history = reply_request.history
    session_manager.dump_session(scenario)

    return ScoreFeedback(scenario=scenario, score=0.9, is_end=False)


@app.get("/tasks", response_model=list[Task])
def get_tasks():
    return TASKS


@app.post("/start_session", response_model=Scenario)
def start_session(task_id: int) -> Scenario:
    task = get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return get_start_session(task)


@app.post("/eval_reply", response_model=ScoreFeedback)
def eval_reply(request: ReplyRequest) -> ScoreFeedback:
    return _eval_reply(request)

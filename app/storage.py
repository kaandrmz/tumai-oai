import random
import json
from pathlib import Path

import pydantic

from app.models import Task, ChatMessage, Scenario


STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)


TASKS = [
    Task(id=1, title="Disease", description="Disease description?"),
    Task(id=2, title="Prognosis", description="Prognosis description?"),
]


def init_session(task: Task) -> Scenario:
    """
    Initializes the session by creating a json file for the task.
    """
    session_id = random.randint(10000, 99999)
    scenario = Scenario(
        session_id=session_id,
        history=[
            ChatMessage(role="teacher", content=task.description),
        ],
    )
    with open(STORAGE_DIR / f"{session_id}.json", "w") as f:
        json.dump(scenario.model_dump(), f)
    return scenario


def load_session(session_id: int) -> Scenario | None:
    """
    Loads the session from the json file.
    """
    try:
        with open(STORAGE_DIR / f"{session_id}.json", "r") as f:
            data = json.load(f)
            scenario = Scenario.model_validate(data)
            return scenario
    except (FileNotFoundError, pydantic.ValidationError):
        return None


def dump_session(scenario: Scenario):
    """
    Dumps the session to the json file.
    """
    with open(STORAGE_DIR / f"{scenario.session_id}.json", "w") as f:
        json.dump(scenario.model_dump(), f)

import random
import json
from pathlib import Path
from typing import Dict

import pydantic

from app.models import Task, ChatMessage


STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)


TASKS = [
    Task(id=1, title="Disease", description="Disease description?"),
    Task(id=2, title="Prognosis", description="Prognosis description?"),
]

class SessionManager:
    def __init__(self, storage_dir: Path = STORAGE_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(exist_ok=True)

    def init_session(self, task: Task) -> Dict:
        """
        Initializes the session by creating a json file for the task.
        """
        session_id = random.randint(10000, 99999)
        scenario = {
            "session_id": session_id,
            "history": [
                ChatMessage(role="teacher", content=task.description),
            ],
        }
        self.dump_session(scenario)
        return scenario

    def load_session(self, session_id: int) -> Dict | None:
        """
        Loads the session from the json file.
        """
        session_file = self.storage_dir / f"{session_id}.json"
        try:
            with open(session_file, "r") as f:
                data = json.load(f)
                return data
        except (FileNotFoundError, pydantic.ValidationError):
            return None

    def dump_session(self, scenario: Dict):
        """
        Dumps the session to the json file.
        """
        session_file = self.storage_dir / f"{scenario['session_id']}.json"
        # Prepare a copy of the scenario for serialization
        scenario_to_dump = scenario.copy()
        # Convert ChatMessage objects to dictionaries
        scenario_to_dump["history"] = [
            msg.model_dump() if isinstance(msg, ChatMessage) else msg
            for msg in scenario["history"]
        ]
        with open(session_file, "w") as f:
            json.dump(scenario_to_dump, f)

    def delete_session(self, session_id: int):
        """
        Deletes the session from the json file.
        """
        session_file = self.storage_dir / f"{session_id}.json"
        session_file.unlink()

import random
import json
from pathlib import Path
from typing import Dict, List, Optional

import pydantic

from app.models import Task, ChatMessage


STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)


TASKS = [
    Task(id=1, title="Diagnostics", description="Disease description?"),
    Task(id=2, title="Hotline", description="Prognosis description?"),
]

class SessionManager:
    def __init__(self, storage_dir: Path = STORAGE_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(exist_ok=True)

    def delete_session(self, session_id: int) -> tuple[bool, str]:
        """
        Deletes the session file.
        """
        if (file := (STORAGE_DIR / f"{session_id}.json")).exists():
            file.unlink()
            return True, f"Session {session_id} deleted successfully."
        else:
            return False, f"Session {session_id} does not exist. Cannot delete."

    def init_session(self, task: Task, session_id: int | None = None) -> Dict:
        """
        Initializes the session by creating a json file for the task.
        Uses the provided session_id if available, otherwise generates a new one.
        Sets initial status to 'active'.
        """
        if session_id is None:
            session_id = random.randint(10000, 99999)
            print(f"No session ID provided, generated new ID: {session_id}")
        else:
            # Check if session already exists with this ID
            if (self.storage_dir / f"{session_id}.json").exists():
                print(f"Warning: Session file for provided ID {session_id} already exists. Overwriting.")
                # Optionally, could raise an error or load existing instead:
                # raise ValueError(f"Session with ID {session_id} already exists.")
            print(f"Using provided session ID: {session_id}")
            
        # Note: History generation now happens in get_start_session in main.py
        # The first message (task description) is no longer added here.
        scenario_data = {
            "session_id": session_id,
            "task_id": task.id,
            "task_title": task.title,
            "task_description": task.description,
            "history": [], # History will be populated by the caller (get_start_session)
            "status": "active",  # Initial status
            "scenario": None, # Will be set by TeacherAgent later
            "diagnosis": None # Will be set by TeacherAgent later
        }
        self.dump_session(scenario_data)
        return scenario_data

    def load_session(self, session_id: int) -> Dict | None:
        """
        Loads the session from the json file.
        """
        session_file = self.storage_dir / f"{session_id}.json"
        try:
            with open(session_file, "r") as f:
                data = json.load(f)
                # Ensure history is parsed back into ChatMessage objects if needed elsewhere
                # For now, just return the raw dict
                return data
        except (FileNotFoundError, json.JSONDecodeError, pydantic.ValidationError) as e:
            print(f"Error loading session {session_id}: {e}")
            return None

    def dump_session(self, scenario: Dict):
        """
        Dumps the session to the json file.
        Ensures 'status' field exists.
        """
        session_file = self.storage_dir / f"{scenario['session_id']}.json"
        # Ensure status is present, default to 'active' if missing
        scenario_to_dump = scenario.copy()
        scenario_to_dump.setdefault("status", "active")

        # Convert ChatMessage objects to dictionaries for serialization
        scenario_to_dump["history"] = [
            msg.model_dump() if isinstance(msg, ChatMessage) else msg
            for msg in scenario.get("history", [])  # Handle potential missing history
        ]

        try:
            with open(session_file, "w") as f:
                json.dump(scenario_to_dump, f, indent=2)  # Add indent for readability
        except IOError as e:
            print(f"Error dumping session {scenario.get('session_id', 'UNKNOWN')}: {e}")

    def list_sessions(self) -> List[Dict[str, str]]:
        """
        Lists all sessions, reading their status from the JSON file.
        Defaults status to 'unknown' if file read fails or status is missing.
        """
        sessions = []
        for session_file in self.storage_dir.glob("*.json"):
            if session_file.is_file() and session_file.stem.isdigit():
                session_id = session_file.stem
                status = "unknown"  # Default status
                try:
                    with open(session_file, "r") as f:
                        data = json.load(f)
                        status = data.get("status", "active")
                except (json.JSONDecodeError, IOError) as e:
                    print(
                        f"Error reading status from {session_file.name}: {e}. Setting status to 'unknown'."
                    )

                sessions.append({"id": session_id, "status": status})
        return sessions

    def update_session_status(self, session_id: int, status: str):
        """Updates the status of a specific session."""
        session = self.load_session(session_id)
        if session:
            session["status"] = status
            self.dump_session(session)
        else:
            print(
                f"Warning: Could not update status for non-existent session {session_id}"
            )

"""
Optimized session manager using SQLite for better performance.
"""
import random
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import threading
import logging

import pydantic

from app.models import Task, ChatMessage

# Configure logging
logger = logging.getLogger(__name__)

# Default storage locations
STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)
DB_PATH = STORAGE_DIR / "sessions.db"

# Sample tasks (should be moved to a database in production)
TASKS = [
    Task(id=1, title="Disease", description="Disease description?"),
    Task(id=2, title="Prognosis", description="Prognosis description?"),
]


class SessionManager:
    """
    Optimized session manager using SQLite for storage and with connection pooling.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path=DB_PATH):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SessionManager, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance

    def __init__(self, db_path=DB_PATH):
        """Initialize the session manager."""
        # Singleton pattern - only initialize once
        if self.initialized:
            return

        self.db_path = db_path
        self.conn = None
        self._init_db()

        # Set up in-memory cache for session data to reduce DB reads
        self._session_cache = {}
        self._cache_expiry = {}  # Track when a cache entry should expire
        self._cache_ttl = 300  # Cache time to live in seconds

        self.initialized = True
        logger.info(f"SessionManager initialized with database at {db_path}")

    def _get_connection(self):
        """Get a database connection, creating one if needed."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            # Enable foreign key support
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Set row factory to get dictionaries
            self.conn.row_factory = sqlite3.Row
        return self.conn

    def _init_db(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create the sessions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY,
            status TEXT DEFAULT 'active',
            scenario TEXT,
            diagnosis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Create the messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
        ''')

        # Create index for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages (session_id)')

        conn.commit()

    def delete_session(self, session_id: int) -> tuple[bool, str]:
        """
        Deletes the session from the database.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Check if the session exists
            cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
            if not cursor.fetchone():
                return False, f"Session {session_id} does not exist. Cannot delete."

            # Delete the session (messages will cascade delete)
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()

            # Remove from cache if present
            if session_id in self._session_cache:
                del self._session_cache[session_id]
                del self._cache_expiry[session_id]

            return True, f"Session {session_id} deleted successfully."
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting session {session_id}: {e}")
            return False, f"Error deleting session {session_id}: {str(e)}"

    def init_session(self, task: Task) -> Dict:
        """
        Initializes the session by creating a new record in the database.
        Sets initial status to 'active'.

        Args:
            task: The task to create a session for

        Returns:
            Dictionary containing session information
        """
        # Generate a random session ID between 10000-99999
        session_id = random.randint(10000, 99999)

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Insert the new session
            cursor.execute(
                "INSERT INTO sessions (id, status) VALUES (?, 'active')",
                (session_id,)
            )

            # Create an initial message with the task description
            cursor.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, "teacher", task.description)
            )

            conn.commit()

            # Create the session object to return
            session = {
                "session_id": session_id,
                "history": [
                    ChatMessage(role="teacher", content=task.description),
                ],
                "status": "active",
            }

            # Cache the session data
            self._cache_session(session)

            return session

        except Exception as e:
            conn.rollback()
            logger.error(f"Error initializing session: {e}")
            raise

    def _cache_session(self, session: Dict):
        """
        Cache a session object in memory for faster access.

        Args:
            session: The session data to cache
        """
        import time
        session_id = session["session_id"]
        self._session_cache[session_id] = session
        self._cache_expiry[session_id] = time.time() + self._cache_ttl

    def _is_cache_valid(self, session_id: int) -> bool:
        """
        Check if a cached session is still valid.

        Args:
            session_id: The session ID to check

        Returns:
            True if the cache is valid, False otherwise
        """
        import time
        if session_id not in self._cache_expiry:
            return False
        return time.time() < self._cache_expiry[session_id]

    def load_session(self, session_id: int) -> Dict | None:
        """
        Loads the session from the database.
        Uses in-memory caching for improved performance.

        Args:
            session_id: The session ID to load

        Returns:
            Dictionary containing session data or None if not found
        """
        # Check if session is in cache and still valid
        if session_id in self._session_cache and self._is_cache_valid(session_id):
            logger.debug(f"Session {session_id} found in cache")
            return self._session_cache[session_id]

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get the session data
            cursor.execute(
                "SELECT id, status, scenario, diagnosis FROM sessions WHERE id = ?",
                (session_id,)
            )
            session_row = cursor.fetchone()

            if not session_row:
                logger.warning(f"Session {session_id} not found in database")
                return None

            # Get the messages
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at",
                (session_id,)
            )
            message_rows = cursor.fetchall()

            # Convert to session object
            session = {
                "session_id": session_row["id"],
                "status": session_row["status"],
                "scenario": session_row["scenario"],
                "diagnosis": session_row["diagnosis"],
                "history": [
                    ChatMessage(role=row["role"], content=row["content"])
                    for row in message_rows
                ]
            }

            # Cache the session data
            self._cache_session(session)

            return session

        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return None

    def dump_session(self, session: Dict):
        """
        Dumps the session to the database.
        Updates the session record and message records.

        Args:
            session: The session data to save
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Update the session data
            cursor.execute(
                "UPDATE sessions SET status = ?, scenario = ?, diagnosis = ? WHERE id = ?",
                (
                    session.get("status", "active"),
                    session.get("scenario", ""),
                    session.get("diagnosis", ""),
                    session["session_id"]
                )
            )

            # Delete existing messages to avoid duplicates
            cursor.execute("DELETE FROM messages WHERE session_id = ?", (session["session_id"],))

            # Insert messages
            for msg in session.get("history", []):
                # Handle both objects and dictionaries
                role = msg.role if hasattr(msg, "role") else msg.get("role", "unknown")
                content = msg.content if hasattr(msg, "content") else msg.get("content", "")

                cursor.execute(
                    "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                    (session["session_id"], role, content)
                )

            conn.commit()

            # Update cache
            self._cache_session(session)

        except Exception as e:
            conn.rollback()
            logger.error(f"Error dumping session {session.get('session_id', 'UNKNOWN')}: {e}")

    def list_sessions(self) -> List[Dict[str, str]]:
        """
        Lists all sessions, reading their status from the database.

        Returns:
            List of dictionaries with session IDs and statuses
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT id, status FROM sessions")
            sessions = [{"id": str(row["id"]), "status": row["status"] or "active"} for row in cursor.fetchall()]

            return sessions

        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    def update_session_status(self, session_id: int, status: str):
        """
        Updates the status of a specific session.

        Args:
            session_id: The session ID to update
            status: The new status
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE sessions SET status = ? WHERE id = ?",
                (status, session_id)
            )

            if cursor.rowcount == 0:
                logger.warning(f"Session {session_id} not found for status update")
            else:
                conn.commit()

                # Update cache if session is cached
                if session_id in self._session_cache:
                    self._session_cache[session_id]["status"] = status

        except Exception as e:
            conn.rollback()
            logger.error(f"Error updating session {session_id} status: {e}")

    def optimize_database(self):
        """
        Optimize the database by running VACUUM and ANALYZE.
        Should be run periodically for optimal performance.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("PRAGMA vacuum")
            cursor.execute("PRAGMA optimize")

            logger.info("Database optimization completed")

        except Exception as e:
            logger.error(f"Error optimizing database: {e}")

    def clear_expired_sessions(self, days_old: int = 30):
        """
        Clear expired sessions older than the specified number of days.

        Args:
            days_old: Age in days for sessions to be considered expired
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM sessions WHERE created_at < datetime('now', ?)",
                (f"-{days_old} days",)
            )

            deleted_count = cursor.rowcount
            conn.commit()

            logger.info(f"Cleared {deleted_count} expired sessions older than {days_old} days")

            # Clear any expired sessions from cache
            self._clean_cache()

        except Exception as e:
            conn.rollback()
            logger.error(f"Error clearing expired sessions: {e}")

    def _clean_cache(self):
        """
        Clean expired entries from the session cache.
        """
        import time
        current_time = time.time()

        expired_keys = [
            key for key, expiry in self._cache_expiry.items()
            if current_time >= expiry
        ]

        for key in expired_keys:
            if key in self._session_cache:
                del self._session_cache[key]
            del self._cache_expiry[key]

        logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
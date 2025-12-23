"""Database setup and connection management"""

import sqlite3
import time
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from .config import config


class Database:
    """SQLite database manager with connection pooling and retry logic"""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.db_path
        self._ensure_initialized()

    def _ensure_initialized(self):
        """Ensure database directory exists and schema is created"""
        config.ensure_db_directory()
        self._create_schema()
        self._cleanup_interrupted_sessions()

    @contextmanager
    def get_connection(self, max_retries: int = 3):
        """
        Get database connection with retry logic for locked database

        Args:
            max_retries: Maximum number of retry attempts

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        last_error = None

        for attempt in range(max_retries):
            try:
                conn = sqlite3.connect(
                    self.db_path,
                    timeout=10.0,
                    isolation_level=None  # Autocommit mode
                )
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                yield conn
                return
            except sqlite3.OperationalError as e:
                last_error = e
                if "locked" in str(e).lower():
                    if attempt < max_retries - 1:
                        # Exponential backoff
                        wait_time = (2 ** attempt) * 0.1
                        time.sleep(wait_time)
                        continue
                raise
            finally:
                if conn:
                    conn.close()

        # If we get here, all retries failed
        raise sqlite3.OperationalError(
            f"Database locked after {max_retries} attempts. "
            "This may be caused by OneDrive sync. Try again in a moment."
        ) from last_error

    def _create_schema(self):
        """Create database tables if they don't exist"""
        schema = """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quick_ref TEXT UNIQUE,
            url TEXT,
            task_id TEXT,
            source TEXT CHECK(source IN ('planner', 'todo', 'local')),
            notes TEXT,
            due_date TEXT,
            created_date TEXT NOT NULL,
            last_worked TEXT
        );

        CREATE TABLE IF NOT EXISTS task_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            type TEXT CHECK(type IN ('file', 'folder', 'url', 'note')),
            value TEXT NOT NULL,
            description TEXT,
            created_date TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            task_description TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            duration_minutes INTEGER,
            target_minutes INTEGER DEFAULT 25,
            intent TEXT,
            outcome TEXT,
            files_modified TEXT,
            working_directory TEXT,
            paused_duration INTEGER DEFAULT 0,
            status TEXT CHECK(status IN ('active', 'completed', 'cancelled')) DEFAULT 'active',
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_start ON sessions(start_time);
        CREATE INDEX IF NOT EXISTS idx_sessions_task ON sessions(task_id);
        CREATE INDEX IF NOT EXISTS idx_tasks_last_worked ON tasks(last_worked);
        """

        with self.get_connection() as conn:
            conn.executescript(schema)

    def _cleanup_interrupted_sessions(self):
        """Mark any active sessions as cancelled on startup (from previous crash/close)"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE sessions
                SET status = 'cancelled',
                    end_time = datetime('now')
                WHERE status = 'active'
            """)

            if cursor.rowcount > 0:
                # Sessions were interrupted - could log this for user awareness
                pass

    def execute(self, query: str, params: tuple = ()):
        """Execute a query and return cursor"""
        with self.get_connection() as conn:
            return conn.execute(query, params)

    def execute_many(self, query: str, params_list: list):
        """Execute a query multiple times with different parameters"""
        with self.get_connection() as conn:
            return conn.executemany(query, params_list)

    def fetch_one(self, query: str, params: tuple = ()):
        """Execute query and fetch one result"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()

    def fetch_all(self, query: str, params: tuple = ()):
        """Execute query and fetch all results"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()


# Global database instance
db = Database()

"""Session management with timer and sleep detection"""

from datetime import datetime, timedelta
from typing import Optional
import time

from .database import db
from .models import Session, Task
from .file_tracker import FileTracker
from .config import config


class SessionManager:
    """Manages work sessions with timer and pause detection"""

    def __init__(self):
        self.current_session: Optional[Session] = None
        self.file_tracker: Optional[FileTracker] = None
        self.last_tick: Optional[datetime] = None
        self.session_start_realtime: Optional[float] = None  # For accurate elapsed time

    def start_session(
        self,
        task: Optional[Task] = None,
        intent: Optional[str] = None,
        working_directory: Optional[str] = None,
        target_minutes: Optional[int] = None
    ) -> Session:
        """
        Start a new work session

        Args:
            task: Associated task (optional)
            intent: What user intends to accomplish
            working_directory: Directory to track files in
            target_minutes: Target duration in minutes

        Returns:
            Created Session object
        """
        if self.current_session:
            raise ValueError("A session is already active. Stop it first.")

        now = datetime.now()
        target = target_minutes or config.default_pomodoro_minutes

        # Create session in database
        cursor = db.execute("""
            INSERT INTO sessions (
                task_id, task_description, start_time, target_minutes,
                intent, working_directory, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'active')
        """, (
            task.id if task else None,
            task.display_name() if task else None,
            now.isoformat(),
            target,
            intent,
            working_directory
        ))

        # Load the created session
        session_row = db.fetch_one("SELECT * FROM sessions WHERE id = ?", (cursor.lastrowid,))
        self.current_session = Session.from_db_row(session_row)

        # Initialize tracking
        self.last_tick = now
        self.session_start_realtime = time.time()

        # Start file tracking if directory specified
        if working_directory:
            self.file_tracker = FileTracker(working_directory)
            self.file_tracker.take_snapshot()
        else:
            self.file_tracker = None

        # Update task's last_worked timestamp
        if task:
            db.execute(
                "UPDATE tasks SET last_worked = ? WHERE id = ?",
                (now.isoformat(), task.id)
            )

        return self.current_session

    def stop_session(self, outcome: Optional[str] = None, files_to_log: Optional[str] = None) -> Session:
        """
        Stop the current session

        Args:
            outcome: What was actually accomplished
            files_to_log: Comma-separated list of files to log

        Returns:
            Completed Session object
        """
        if not self.current_session:
            raise ValueError("No active session to stop")

        now = datetime.now()
        start_dt = self.current_session.get_start_datetime()
        duration_minutes = int((now - start_dt).total_seconds() / 60)

        # Update session in database
        db.execute("""
            UPDATE sessions
            SET end_time = ?,
                duration_minutes = ?,
                outcome = ?,
                files_modified = ?,
                status = 'completed'
            WHERE id = ?
        """, (
            now.isoformat(),
            duration_minutes,
            outcome,
            files_to_log,
            self.current_session.id
        ))

        # Reload session
        session_row = db.fetch_one("SELECT * FROM sessions WHERE id = ?", (self.current_session.id,))
        completed_session = Session.from_db_row(session_row)

        # Clear current session
        self.current_session = None
        self.file_tracker = None
        self.last_tick = None
        self.session_start_realtime = None

        return completed_session

    def cancel_session(self) -> Session:
        """
        Cancel the current session without logging outcome

        Returns:
            Cancelled Session object
        """
        if not self.current_session:
            raise ValueError("No active session to cancel")

        now = datetime.now()

        db.execute("""
            UPDATE sessions
            SET end_time = ?,
                status = 'cancelled'
            WHERE id = ?
        """, (now.isoformat(), self.current_session.id))

        # Reload session
        session_row = db.fetch_one("SELECT * FROM sessions WHERE id = ?", (self.current_session.id,))
        cancelled_session = Session.from_db_row(session_row)

        # Clear current session
        self.current_session = None
        self.file_tracker = None
        self.last_tick = None
        self.session_start_realtime = None

        return cancelled_session

    def extend_session(self, additional_minutes: int = 25):
        """
        Extend the current session target

        Args:
            additional_minutes: Minutes to add to target
        """
        if not self.current_session:
            raise ValueError("No active session to extend")

        new_target = self.current_session.target_minutes + additional_minutes

        db.execute("""
            UPDATE sessions
            SET target_minutes = ?
            WHERE id = ?
        """, (new_target, self.current_session.id))

        self.current_session.target_minutes = new_target

    def pause_session(self, pause_duration_minutes: int):
        """
        Add paused time to the session (for sleep/away detection)

        Args:
            pause_duration_minutes: Minutes to add to paused duration
        """
        if not self.current_session:
            return

        new_paused = self.current_session.paused_duration + pause_duration_minutes

        db.execute("""
            UPDATE sessions
            SET paused_duration = ?
            WHERE id = ?
        """, (new_paused, self.current_session.id))

        self.current_session.paused_duration = new_paused

    def check_for_sleep_gap(self) -> Optional[int]:
        """
        Check if there's been a significant time gap (potential sleep/lock)

        Returns:
            Minutes of gap if detected, None otherwise
        """
        if not self.current_session or not self.last_tick:
            return None

        now = datetime.now()
        gap = (now - self.last_tick).total_seconds() / 60

        if gap > config.sleep_gap_threshold_minutes:
            return int(gap)

        return None

    def update_tick(self):
        """Update the last tick timestamp (call regularly to detect gaps)"""
        self.last_tick = datetime.now()

    def get_elapsed_minutes(self) -> int:
        """Get elapsed minutes in current session"""
        if not self.current_session:
            return 0

        if self.session_start_realtime:
            # Use real-time elapsed (more accurate for live display)
            elapsed_seconds = time.time() - self.session_start_realtime
            return int(elapsed_seconds / 60)
        else:
            # Fallback to datetime calculation
            start_dt = self.current_session.get_start_datetime()
            elapsed = (datetime.now() - start_dt).total_seconds() / 60
            return int(elapsed)

    def get_remaining_minutes(self) -> int:
        """Get remaining minutes in current session"""
        if not self.current_session:
            return 0

        elapsed = self.get_elapsed_minutes()
        remaining = self.current_session.target_minutes - elapsed
        return max(0, remaining)

    def is_overtime(self) -> bool:
        """Check if session has exceeded target"""
        if not self.current_session:
            return False

        return self.get_elapsed_minutes() >= self.current_session.target_minutes

    def get_modified_files(self):
        """Get list of files modified during session"""
        if not self.file_tracker:
            return []

        return self.file_tracker.get_modified_files()

    def get_last_session_time(self) -> Optional[datetime]:
        """Get the end time of the most recent completed session"""
        row = db.fetch_one("""
            SELECT end_time FROM sessions
            WHERE status = 'completed' AND end_time IS NOT NULL
            ORDER BY end_time DESC
            LIMIT 1
        """)

        if row and row['end_time']:
            return datetime.fromisoformat(row['end_time'])

        return None


# Global session manager instance
session_manager = SessionManager()

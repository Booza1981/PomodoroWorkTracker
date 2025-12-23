"""Configuration management for Pomodoro Task Tracker"""

import os
from pathlib import Path
from datetime import time
from dotenv import load_dotenv


class Config:
    """Application configuration loaded from .env and environment variables"""

    def __init__(self):
        # Load .env file from project root
        env_path = Path(__file__).parent.parent / '.env'
        load_dotenv(env_path)

        # OneDrive path
        self.onedrive_path = self._get_onedrive_path()
        self.db_path = Path(self.onedrive_path) / 'PomodoroTracker' / 'pomodoro.db'

        # Work hours
        self.work_start = self._parse_time(os.getenv('WORK_START', '09:00'))
        self.work_end = self._parse_time(os.getenv('WORK_END', '17:00'))
        self.lunch_start = self._parse_time(os.getenv('LUNCH_START', '12:00'))
        self.lunch_end = self._parse_time(os.getenv('LUNCH_END', '13:00'))

        # Session defaults
        self.default_pomodoro_minutes = int(os.getenv('DEFAULT_POMODORO_MINUTES', '25'))
        self.idle_warning_minutes = int(os.getenv('IDLE_WARNING_MINUTES', '30'))

        # Behavior
        self.auto_pause_on_sleep = self._parse_bool(os.getenv('AUTO_PAUSE_ON_SLEEP', 'true'))
        self.show_file_tracking = self._parse_bool(os.getenv('SHOW_FILE_TRACKING', 'true'))

        # Session check interval
        self.long_session_warning_hours = 2
        self.sleep_gap_threshold_minutes = 5  # Consider >5min gap as potential sleep

    def _get_onedrive_path(self) -> str:
        """Get OneDrive path from .env or environment variables"""
        # First check .env file
        env_path = os.getenv('ONEDRIVE_PATH')
        if env_path and Path(env_path).exists():
            return env_path

        # Try OneDriveCommercial (work/school account)
        onedrive_commercial = os.getenv('OneDriveCommercial')
        if onedrive_commercial and Path(onedrive_commercial).exists():
            return onedrive_commercial

        # Try OneDrive (personal account)
        onedrive = os.getenv('OneDrive')
        if onedrive and Path(onedrive).exists():
            return onedrive

        # Fallback to user home directory
        return str(Path.home())

    def _parse_time(self, time_str: str) -> time:
        """Parse time string in HH:MM format"""
        try:
            hour, minute = time_str.split(':')
            return time(int(hour), int(minute))
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM")

    def _parse_bool(self, value: str) -> bool:
        """Parse boolean string"""
        return value.lower() in ('true', '1', 'yes', 'on')

    def is_work_hours(self, check_time: time = None) -> bool:
        """Check if given time (or now) is within work hours, excluding lunch"""
        from datetime import datetime
        if check_time is None:
            check_time = datetime.now().time()

        # Outside work hours
        if check_time < self.work_start or check_time >= self.work_end:
            return False

        # During lunch
        if self.lunch_start <= check_time < self.lunch_end:
            return False

        return True

    def ensure_db_directory(self):
        """Ensure database directory exists"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()

"""Data models for tasks, resources, and sessions"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Task:
    """Represents a work task"""
    id: Optional[int]
    name: str
    quick_ref: Optional[str]
    url: Optional[str]
    task_id: Optional[str]
    source: str  # 'planner', 'todo', 'local'
    notes: Optional[str]
    due_date: Optional[str]
    created_date: str
    last_worked: Optional[str]

    @classmethod
    def from_db_row(cls, row) -> 'Task':
        """Create Task from database row"""
        return cls(
            id=row['id'],
            name=row['name'],
            quick_ref=row['quick_ref'],
            url=row['url'],
            task_id=row['task_id'],
            source=row['source'],
            notes=row['notes'],
            due_date=row['due_date'],
            created_date=row['created_date'],
            last_worked=row['last_worked']
        )

    def display_name(self) -> str:
        """Get display name with optional quick reference"""
        if self.quick_ref:
            return f"{self.name} ({self.quick_ref})"
        return self.name


@dataclass
class TaskResource:
    """Represents a resource associated with a task"""
    id: Optional[int]
    task_id: int
    type: str  # 'file', 'folder', 'url', 'note'
    value: str
    description: Optional[str]
    created_date: str

    @classmethod
    def from_db_row(cls, row) -> 'TaskResource':
        """Create TaskResource from database row"""
        return cls(
            id=row['id'],
            task_id=row['task_id'],
            type=row['type'],
            value=row['value'],
            description=row['description'],
            created_date=row['created_date']
        )

    def display_icon(self) -> str:
        """Get icon for resource type (ASCII for CMD compatibility)"""
        icons = {
            'file': '[FILE]',
            'folder': '[DIR]',
            'url': '[URL]',
            'note': '[NOTE]'
        }
        return icons.get(self.type, '[?]')


@dataclass
class Session:
    """Represents a work session"""
    id: Optional[int]
    task_id: Optional[int]
    task_description: Optional[str]
    start_time: str
    end_time: Optional[str]
    duration_minutes: Optional[int]
    target_minutes: int
    intent: Optional[str]
    outcome: Optional[str]
    files_modified: Optional[str]
    working_directory: Optional[str]
    paused_duration: int
    status: str  # 'active', 'completed', 'cancelled'

    @classmethod
    def from_db_row(cls, row) -> 'Session':
        """Create Session from database row"""
        return cls(
            id=row['id'],
            task_id=row['task_id'],
            task_description=row['task_description'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            duration_minutes=row['duration_minutes'],
            target_minutes=row['target_minutes'],
            intent=row['intent'],
            outcome=row['outcome'],
            files_modified=row['files_modified'],
            working_directory=row['working_directory'],
            paused_duration=row['paused_duration'],
            status=row['status']
        )

    def get_files_list(self) -> List[str]:
        """Get list of modified files"""
        if not self.files_modified:
            return []
        return [f.strip() for f in self.files_modified.split(',') if f.strip()]

    def get_start_datetime(self) -> datetime:
        """Get start time as datetime"""
        return datetime.fromisoformat(self.start_time)

    def get_end_datetime(self) -> Optional[datetime]:
        """Get end time as datetime"""
        if self.end_time:
            return datetime.fromisoformat(self.end_time)
        return None

    def get_actual_duration(self) -> Optional[int]:
        """Get actual duration in minutes (excluding paused time)"""
        if self.duration_minutes is None:
            return None
        return max(0, self.duration_minutes - self.paused_duration)

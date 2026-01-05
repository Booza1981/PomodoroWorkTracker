"""Task management operations"""

from datetime import datetime
from typing import List, Optional

from .database import db
from .models import Task, TaskResource


class TaskManager:
    """Manages tasks and task resources"""

    def create_task(
        self,
        name: str,
        source: str = 'local',
        quick_ref: Optional[str] = None,
        url: Optional[str] = None,
        task_id: Optional[str] = None,
        notes: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> Task:
        """
        Create a new task

        Args:
            name: Task name
            source: Task source ('planner', 'todo', 'local')
            quick_ref: Optional quick reference code
            url: Optional task URL
            task_id: Optional external task ID
            notes: Optional notes
            due_date: Optional due date

        Returns:
            Created Task object
        """
        now = datetime.now().isoformat()

        cursor = db.execute("""
            INSERT INTO tasks (
                name, quick_ref, url, task_id, source, notes, due_date, created_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, quick_ref, url, task_id, source, notes, due_date, now))

        task_row = db.fetch_one("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,))
        return Task.from_db_row(task_row)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get task by ID"""
        row = db.fetch_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return Task.from_db_row(row) if row else None

    def get_task_by_quick_ref(self, quick_ref: str) -> Optional[Task]:
        """Get task by quick reference"""
        row = db.fetch_one("SELECT * FROM tasks WHERE quick_ref = ?", (quick_ref,))
        return Task.from_db_row(row) if row else None

    def get_all_tasks(self, limit: Optional[int] = None) -> List[Task]:
        """
        Get all tasks ordered by last worked (most recent first)

        Args:
            limit: Optional limit on number of tasks

        Returns:
            List of Task objects
        """
        query = """
            SELECT * FROM tasks
            ORDER BY
                CASE WHEN last_worked IS NULL THEN 1 ELSE 0 END,
                last_worked DESC,
                created_date DESC
        """
        if limit:
            query += f" LIMIT {limit}"

        rows = db.fetch_all(query)
        return [Task.from_db_row(row) for row in rows]

    def get_recent_tasks(self, limit: int = 10) -> List[Task]:
        """
        Get recently worked tasks

        Args:
            limit: Number of tasks to return

        Returns:
            List of Task objects
        """
        rows = db.fetch_all("""
            SELECT * FROM tasks
            WHERE last_worked IS NOT NULL
            ORDER BY last_worked DESC
            LIMIT ?
        """, (limit,))

        return [Task.from_db_row(row) for row in rows]

    def search_tasks(self, search_term: str) -> List[Task]:
        """
        Search tasks by name, quick_ref, or notes

        Args:
            search_term: Search string

        Returns:
            List of matching Task objects
        """
        pattern = f"%{search_term}%"
        rows = db.fetch_all("""
            SELECT * FROM tasks
            WHERE name LIKE ? OR quick_ref LIKE ? OR notes LIKE ?
            ORDER BY last_worked DESC, created_date DESC
        """, (pattern, pattern, pattern))

        return [Task.from_db_row(row) for row in rows]

    def update_task(
        self,
        task_id: int,
        name: Optional[str] = None,
        quick_ref: Optional[str] = None,
        url: Optional[str] = None,
        task_id_field: Optional[str] = None,
        notes: Optional[str] = None,
        due_date: Optional[str] = None
    ):
        """Update task fields"""
        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if quick_ref is not None:
            updates.append("quick_ref = ?")
            params.append(quick_ref)
        if url is not None:
            updates.append("url = ?")
            params.append(url)
        if task_id_field is not None:
            updates.append("task_id = ?")
            params.append(task_id_field)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if due_date is not None:
            updates.append("due_date = ?")
            params.append(due_date)

        if not updates:
            return

        params.append(task_id)
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
        db.execute(query, tuple(params))

    def delete_task(self, task_id: int):
        """Delete a task and its resources"""
        db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    # Task Resources

    def add_resource(
        self,
        task_id: int,
        resource_type: str,
        value: str,
        description: Optional[str] = None
    ) -> TaskResource:
        """
        Add a resource to a task

        Args:
            task_id: Task ID
            resource_type: Resource type ('file', 'folder', 'url', 'note')
            value: Resource value (path, URL, or note text)
            description: Optional description

        Returns:
            Created TaskResource object
        """
        now = datetime.now().isoformat()

        cursor = db.execute("""
            INSERT INTO task_resources (task_id, type, value, description, created_date)
            VALUES (?, ?, ?, ?, ?)
        """, (task_id, resource_type, value, description, now))

        resource_row = db.fetch_one("SELECT * FROM task_resources WHERE id = ?", (cursor.lastrowid,))
        return TaskResource.from_db_row(resource_row)

    def get_task_resources(self, task_id: int) -> List[TaskResource]:
        """Get all resources for a task"""
        rows = db.fetch_all("""
            SELECT * FROM task_resources
            WHERE task_id = ?
            ORDER BY created_date ASC
        """, (task_id,))

        return [TaskResource.from_db_row(row) for row in rows]

    def update_resource(
        self,
        resource_id: int,
        resource_type: Optional[str] = None,
        value: Optional[str] = None,
        description: Optional[str] = None
    ):
        """
        Update a task resource

        Args:
            resource_id: Resource ID
            resource_type: Optional new resource type
            value: Optional new value
            description: Optional new description
        """
        updates = []
        params = []

        if resource_type is not None:
            updates.append("type = ?")
            params.append(resource_type)
        if value is not None:
            updates.append("value = ?")
            params.append(value)
        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if not updates:
            return

        params.append(resource_id)
        query = f"UPDATE task_resources SET {', '.join(updates)} WHERE id = ?"
        db.execute(query, tuple(params))

    def delete_resource(self, resource_id: int):
        """Delete a task resource"""
        db.execute("DELETE FROM task_resources WHERE id = ?", (resource_id,))

    # Task History

    def get_task_sessions(self, task_id: int, limit: Optional[int] = None, include_all_statuses: bool = True):
        """
        Get all sessions for a task

        Args:
            task_id: Task ID
            limit: Optional limit on number of sessions
            include_all_statuses: If True, include all sessions regardless of status.
                                  If False, only include completed sessions.

        Returns:
            List of Session objects
        """
        from .models import Session

        if include_all_statuses:
            query = """
                SELECT * FROM sessions
                WHERE task_id = ?
                ORDER BY start_time DESC
            """
        else:
            query = """
                SELECT * FROM sessions
                WHERE task_id = ? AND status = 'completed'
                ORDER BY start_time DESC
            """
        if limit:
            query += f" LIMIT {limit}"

        rows = db.fetch_all(query, (task_id,))
        return [Session.from_db_row(row) for row in rows]

    def get_task_total_time(self, task_id: int) -> int:
        """
        Get total time spent on a task in minutes

        Args:
            task_id: Task ID

        Returns:
            Total minutes
        """
        row = db.fetch_one("""
            SELECT SUM(duration_minutes - paused_duration) as total
            FROM sessions
            WHERE task_id = ? AND status = 'completed'
        """, (task_id,))

        return row['total'] if row and row['total'] else 0


# Global task manager instance
task_manager = TaskManager()

"""Reporting functionality for work sessions and tasks"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from collections import defaultdict

from .database import db
from .models import Session, Task
from .config import config


class Reporter:
    """Generates reports on work sessions and tasks"""

    def get_today_sessions(self) -> List[Session]:
        """Get all sessions from today"""
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time()).isoformat()
        tomorrow_start = datetime.combine(today + timedelta(days=1), datetime.min.time()).isoformat()

        rows = db.fetch_all("""
            SELECT * FROM sessions
            WHERE start_time >= ? AND start_time < ? AND status = 'completed'
            ORDER BY start_time ASC
        """, (today_start, tomorrow_start))

        return [Session.from_db_row(row) for row in rows]

    def get_week_sessions(self, week_offset: int = 0) -> List[Session]:
        """
        Get all sessions from a specific week

        Args:
            week_offset: 0 for current week, -1 for last week, etc.

        Returns:
            List of Session objects
        """
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=7)

        week_start_dt = datetime.combine(week_start, datetime.min.time()).isoformat()
        week_end_dt = datetime.combine(week_end, datetime.min.time()).isoformat()

        rows = db.fetch_all("""
            SELECT * FROM sessions
            WHERE start_time >= ? AND start_time < ? AND status = 'completed'
            ORDER BY start_time ASC
        """, (week_start_dt, week_end_dt))

        return [Session.from_db_row(row) for row in rows]

    def get_date_range_sessions(self, start_date: datetime, end_date: datetime) -> List[Session]:
        """Get all sessions within a date range"""
        rows = db.fetch_all("""
            SELECT * FROM sessions
            WHERE start_time >= ? AND start_time < ? AND status = 'completed'
            ORDER BY start_time ASC
        """, (start_date.isoformat(), end_date.isoformat()))

        return [Session.from_db_row(row) for row in rows]

    def group_sessions_by_task(self, sessions: List[Session]) -> Dict[str, List[Session]]:
        """
        Group sessions by task

        Returns:
            Dict mapping task description to list of sessions
        """
        grouped = defaultdict(list)

        for session in sessions:
            key = session.task_description or "Ad-hoc work"
            grouped[key].append(session)

        return dict(grouped)

    def calculate_total_time(self, sessions: List[Session]) -> int:
        """
        Calculate total time from sessions in minutes

        Args:
            sessions: List of Session objects

        Returns:
            Total minutes
        """
        total = 0
        for session in sessions:
            if session.duration_minutes:
                actual_duration = session.duration_minutes - session.paused_duration
                total += max(0, actual_duration)
        return total

    def format_duration(self, minutes: int) -> str:
        """Format duration in human-readable format"""
        hours = minutes // 60
        mins = minutes % 60

        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"

    def generate_daily_report(self) -> str:
        """Generate today's work summary"""
        sessions = self.get_today_sessions()

        if not sessions:
            return "No work sessions today."

        total_time = self.calculate_total_time(sessions)
        grouped = self.group_sessions_by_task(sessions)

        lines = [
            f"Today's Summary - {datetime.now().strftime('%A, %B %d, %Y')}",
            "=" * 60,
            f"Total: {self.format_duration(total_time)} across {len(sessions)} sessions",
            "",
            "By Task:",
            "-" * 60
        ]

        for task_desc, task_sessions in grouped.items():
            task_time = self.calculate_total_time(task_sessions)
            lines.append(f"{task_desc} - {self.format_duration(task_time)} ({len(task_sessions)} sessions)")

        return "\n".join(lines)

    def generate_weekly_report(self, week_offset: int = 0) -> str:
        """Generate weekly work summary"""
        sessions = self.get_week_sessions(week_offset)

        if not sessions:
            return "No work sessions this week."

        total_time = self.calculate_total_time(sessions)
        grouped = self.group_sessions_by_task(sessions)

        # Calculate week range
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=6)

        lines = [
            f"Week of {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}",
            "=" * 60,
            f"Total: {self.format_duration(total_time)} across {len(sessions)} sessions",
            "",
            "By Task:",
            "=" * 60
        ]

        for task_desc, task_sessions in sorted(grouped.items(), key=lambda x: self.calculate_total_time(x[1]), reverse=True):
            task_time = self.calculate_total_time(task_sessions)
            lines.append(f"\n{task_desc} - {self.format_duration(task_time)} ({len(task_sessions)} sessions)")

            # Get task URL if available
            if task_sessions[0].task_id:
                task_row = db.fetch_one("SELECT url FROM tasks WHERE id = ?", (task_sessions[0].task_id,))
                if task_row and task_row['url']:
                    lines.append(f"  Link: {task_row['url']}")

            # Show intent/outcome highlights
            highlights = []
            for session in task_sessions[:3]:  # Show up to 3 sessions
                if session.intent and session.outcome:
                    highlights.append(f"  • {session.intent} → {session.outcome}")
                elif session.intent:
                    highlights.append(f"  • {session.intent}")

            if highlights:
                lines.append("  Intent → Outcome highlights:")
                lines.extend(highlights)

            # Show unique files
            all_files = set()
            for session in task_sessions:
                all_files.update(session.get_files_list())

            if all_files:
                file_counts = {}
                for session in task_sessions:
                    for file in session.get_files_list():
                        file_counts[file] = file_counts.get(file, 0) + 1

                top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                files_str = ", ".join(f"{f} ({c}x)" if c > 1 else f for f, c in top_files)
                lines.append(f"  Files: {files_str}")

        return "\n".join(lines)

    def generate_task_report(self, task_id: int) -> str:
        """Generate report for a specific task"""
        from .tasks import task_manager

        task = task_manager.get_task(task_id)
        if not task:
            return "Task not found."

        sessions = task_manager.get_task_sessions(task_id, include_all_statuses=False)
        total_time = task_manager.get_task_total_time(task_id)

        lines = [
            f"Task: {task.display_name()}",
            "=" * 60,
            f"Total time: {self.format_duration(total_time)} across {len(sessions)} sessions",
            ""
        ]

        if task.url:
            lines.append(f"Link: {task.url}")
            lines.append("")

        if task.notes:
            lines.append(f"Notes: {task.notes}")
            lines.append("")

        # Show resources
        resources = task_manager.get_task_resources(task_id)
        if resources:
            lines.append("Resources:")
            for res in resources:
                lines.append(f"  {res.display_icon()} {res.value}")
                if res.description:
                    lines.append(f"     {res.description}")
            lines.append("")

        # Show session history
        if sessions:
            lines.append("Session History:")
            lines.append("-" * 60)

            for session in sessions:
                start = session.get_start_datetime()
                duration = session.duration_minutes - session.paused_duration
                lines.append(f"{start.strftime('%Y-%m-%d %H:%M')} - {self.format_duration(duration)}")

                if session.intent:
                    lines.append(f"  Intent: {session.intent}")
                if session.outcome:
                    lines.append(f"  Outcome: {session.outcome}")

                files = session.get_files_list()
                if files:
                    lines.append(f"  Files: {', '.join(files[:3])}")
                    if len(files) > 3:
                        lines.append(f"    ... and {len(files) - 3} more")

                lines.append("")

        return "\n".join(lines)

    def export_report(self, content: str, filename: Optional[str] = None) -> Path:
        """
        Export report to a markdown file

        Args:
            content: Report content
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to exported file
        """
        if not filename:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
            filename = f"pomodoro_report_{timestamp}.md"

        # Save to OneDrive reports directory
        reports_dir = Path(config.onedrive_path) / 'PomodoroTracker' / 'Reports'
        reports_dir.mkdir(parents=True, exist_ok=True)

        file_path = reports_dir / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_path


# Global reporter instance
reporter = Reporter()

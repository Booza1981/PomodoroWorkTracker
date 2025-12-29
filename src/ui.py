"""Rich UI components for terminal interface"""

import os
import subprocess
import platform
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Prompt, Confirm
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box

from .models import Task, TaskResource, Session
from .config import config


console = Console()


def prompt_open_resources(task: Task, resources: List[TaskResource]) -> bool:
    """
    Prompt user to select and open resources (supports single, multiple, or all)

    Args:
        task: Task object (for accessing task URL)
        resources: List of TaskResource objects

    Returns:
        True if user opened something, False if cancelled
    """
    if not resources and not task.url:
        print_info("This task has no resources or URL")
        return False

    console.print("\n[bold]Available to open:[/bold]")

    # Show task URL first if available
    url_option = None
    if task.url:
        console.print(f"  0. [URL] Task link ({task.source or 'external'})")
        url_option = 0

    # Show resources
    for idx, res in enumerate(resources, 1):
        icon = res.display_icon()
        console.print(f"  {idx}. {icon} {res.value}")

    max_num = len(resources)
    prompt_text = f"\nOpen which? [0-{max_num}, 'all', or '1,2,3' or Enter to skip]" if url_option is not None else f"\nOpen which? [1-{max_num}, 'all', or '1,2,3' or Enter to skip]"

    choice = Prompt.ask(prompt_text, default="").strip()

    if not choice:
        return False

    indices_to_open = []
    open_url = False

    if choice.lower() == 'all':
        if url_option is not None:
            open_url = True
        indices_to_open = list(range(len(resources)))
    else:
        try:
            # Parse comma-separated numbers
            for part in choice.split(','):
                idx = int(part.strip())
                if idx == 0 and url_option is not None:
                    open_url = True
                elif 1 <= idx <= len(resources):
                    indices_to_open.append(idx - 1)
        except ValueError:
            print_error("Invalid selection")
            return False

    # Open task URL if selected
    if open_url and task.url:
        try:
            import os
            import platform
            import subprocess

            if platform.system() == 'Windows':
                os.startfile(task.url)
            elif platform.system() == 'Darwin':
                subprocess.run(['open', task.url])
            else:
                subprocess.run(['xdg-open', task.url])
            print_success(f"Opening task link: {task.url}")
        except Exception as e:
            print_error(f"Could not open task URL: {e}")

    # Open selected resources
    for idx in indices_to_open:
        open_resource(resources[idx])

    return len(indices_to_open) > 0 or open_url


def open_resource(resource: TaskResource):
    """Open a resource (file, folder, or URL) in the default application"""
    try:
        value = resource.value

        # Handle URLs
        if resource.type == 'url':
            if platform.system() == 'Windows':
                try:
                    os.startfile(value)
                    print_success(f"Opening URL: {value}")
                except Exception as e:
                    print_error(f"Could not open URL: {e}")
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', value])
                print_success(f"Opening URL: {value}")
            else:  # Linux
                subprocess.run(['xdg-open', value])
                print_success(f"Opening URL: {value}")

        # Handle files and folders
        elif resource.type in ['file', 'folder']:
            path = Path(value)

            if not path.exists():
                print_warning(f"Path does not exist: {value}")
                print_info(f"Looking for: {path.absolute()}")
                return

            if platform.system() == 'Windows':
                try:
                    os.startfile(str(path))
                    resource_type_str = "folder" if resource.type == 'folder' else "file"
                    print_success(f"Opening {resource_type_str}: {value}")
                except Exception as e:
                    print_error(f"Could not open {resource.type}: {e}")
                    print_info(f"Tried to open: {path.absolute()}")
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(path)])
                print_success(f"Opening: {value}")
            else:  # Linux
                subprocess.run(['xdg-open', str(path)])
                print_success(f"Opening: {value}")

        # Handle notes (just display them)
        elif resource.type == 'note':
            console.print(f"\n[cyan]Note:[/cyan] {value}")

    except Exception as e:
        print_error(f"Could not open resource: {e}")
        import traceback
        print_error(traceback.format_exc())


def print_error(message: str):
    """Print error message"""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str):
    """Print success message"""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_info(message: str):
    """Print info message"""
    console.print(f"[cyan]ℹ[/cyan] {message}")


def print_warning(message: str):
    """Print warning message"""
    console.print(f"[yellow]⚠[/yellow] {message}")


def prompt_task_selection(tasks: List[Task], allow_new: bool = True, allow_none: bool = True) -> Optional[int]:
    """
    Display task selection menu and get user choice

    Args:
        tasks: List of tasks to display
        allow_new: Allow creating a new task
        allow_none: Allow selecting no task (ad-hoc work)

    Returns:
        Selected task index, -1 for new task, None for no task
    """
    if not tasks and not allow_new:
        return None

    console.print("\n[bold]Recent tasks:[/bold]")

    table = Table(show_header=True, box=box.SIMPLE)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Task", style="white")
    table.add_column("Last Worked", style="dim")

    for idx, task in enumerate(tasks, 1):
        last_worked = "Never"
        if task.last_worked:
            last_dt = datetime.fromisoformat(task.last_worked)
            delta = datetime.now() - last_dt

            if delta.days == 0:
                last_worked = "Today"
            elif delta.days == 1:
                last_worked = "Yesterday"
            elif delta.days < 7:
                last_worked = f"{delta.days} days ago"
            else:
                last_worked = last_dt.strftime('%b %d')

        table.add_row(str(idx), task.display_name(), last_worked)

    if allow_new:
        table.add_row("n", "[italic]New task[/italic]", "")

    if allow_none:
        table.add_row("", "[dim]Press Enter for ad-hoc work[/dim]", "")

    console.print(table)

    while True:
        choice = Prompt.ask("\nSelect task", default="").strip().lower()

        if not choice and allow_none:
            return None

        if choice == 'n' and allow_new:
            return -1

        try:
            idx = int(choice)
            if 1 <= idx <= len(tasks):
                return idx - 1
        except ValueError:
            pass

        print_error("Invalid selection. Try again.")


def display_task_details(task: Task, resources: List[TaskResource], recent_sessions: List[Session], show_open_prompt: bool = True):
    """Display detailed task information"""
    lines = []

    # Header
    lines.append(f"[bold cyan]{task.display_name()}[/bold cyan]")

    # URL
    if task.url:
        lines.append(f"[link={task.url}]{task.url}[/link]")

    # Resources
    if resources:
        lines.append("\n[bold]Resources:[/bold]")
        for idx, res in enumerate(resources, 1):
            icon = res.display_icon()
            lines.append(f"  {idx}. {icon} {res.value}")
            if res.description:
                lines.append(f"     [dim]{res.description}[/dim]")

    # Notes
    if task.notes:
        lines.append(f"\n[bold]Notes:[/bold]\n{task.notes}")

    # Recent work
    if recent_sessions:
        lines.append("\n[bold]Recent work:[/bold]")
        for session in recent_sessions[:3]:
            start = session.get_start_datetime()
            duration = session.duration_minutes - session.paused_duration
            delta = datetime.now() - start

            if delta.days == 0:
                when = "Today"
            elif delta.days == 1:
                when = "Yesterday"
            else:
                when = f"{delta.days} days ago"

            intent_summary = session.intent[:50] + "..." if session.intent and len(session.intent) > 50 else session.intent
            lines.append(f"  • {when}: {intent_summary} ({duration}m)")

    panel = Panel(
        "\n".join(lines),
        box=box.ROUNDED,
        border_style="cyan"
    )

    console.print(panel)

    # Prompt to open resources (supports multiple/all/task URL)
    if show_open_prompt and (resources or task.url):
        prompt_open_resources(task, resources)


def prompt_create_task() -> Dict[str, str]:
    """Interactive task creation"""
    console.print("\n[bold]Create New Task[/bold]")

    name = Prompt.ask("Task name")
    quick_ref = Prompt.ask("Quick reference (optional)", default="") or None

    source_choices = {
        '1': 'planner',
        '2': 'todo',
        '3': 'local'
    }

    console.print("\nTask source:")
    console.print("  1. Microsoft Planner")
    console.print("  2. Microsoft To Do")
    console.print("  3. Local (no external link)")

    source_choice = Prompt.ask("Select", choices=['1', '2', '3'], default='3')
    source = source_choices[source_choice]

    url = None
    if source in ['planner', 'todo']:
        url = Prompt.ask(f"{source.title()} URL (or Enter to skip)", default="") or None

    notes = Prompt.ask("Notes (optional)", default="") or None

    return {
        'name': name,
        'quick_ref': quick_ref,
        'url': url,
        'source': source,
        'notes': notes
    }


def prompt_add_resources(task_id: int) -> bool:
    """Prompt to add resources to a task"""
    if not Confirm.ask("\nAdd resources?", default=False):
        return False

    from .tasks import task_manager

    while True:
        console.print("\nResource type: [cyan]file[/cyan], [cyan]folder[/cyan], [cyan]url[/cyan], [cyan]note[/cyan], or [cyan]done[/cyan]")
        res_type = Prompt.ask("Type", default="done").lower()

        if res_type == 'done':
            break

        if res_type not in ['file', 'folder', 'url', 'note']:
            print_error("Invalid type")
            continue

        if res_type == 'file':
            value = Prompt.ask("File path")
        elif res_type == 'folder':
            value = Prompt.ask("Folder path")
        elif res_type == 'url':
            value = Prompt.ask("URL")
        else:  # note
            value = Prompt.ask("Note")

        description = Prompt.ask("Description (optional)", default="") or None

        task_manager.add_resource(task_id, res_type, value, description)
        print_success(f"Added {res_type}")

    return True


def prompt_file_selection(files: List[Dict]) -> Optional[str]:
    """
    Prompt user to select which files to log

    Args:
        files: List of file dicts with 'rel_path' and 'modified_time'

    Returns:
        Comma-separated string of selected file paths, or None
    """
    if not files:
        return None

    console.print("\n[bold]Files modified during session:[/bold]")

    table = Table(show_header=True, box=box.SIMPLE)
    table.add_column("#", style="cyan", width=4)
    table.add_column("File", style="white")
    table.add_column("Modified", style="dim")

    for idx, file in enumerate(files, 1):
        mod_time = file['modified_time'].strftime('%H:%M')
        table.add_row(str(idx), file['rel_path'], mod_time)

    console.print(table)

    choice = Prompt.ask(
        "\nSelect files to log",
        default="all"
    ).strip().lower()

    if choice == 'all' or not choice:
        return ", ".join(f['rel_path'] for f in files)

    # Parse selection (e.g., "1,2,4" or "1-3")
    selected_files = []
    try:
        for part in choice.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-')
                for i in range(int(start), int(end) + 1):
                    if 1 <= i <= len(files):
                        selected_files.append(files[i - 1]['rel_path'])
            else:
                i = int(part)
                if 1 <= i <= len(files):
                    selected_files.append(files[i - 1]['rel_path'])

        return ", ".join(selected_files) if selected_files else None

    except (ValueError, IndexError):
        print_error("Invalid selection")
        return None


def create_timer_display(session: Session, elapsed_minutes: int, remaining_minutes: int) -> str:
    """Create live timer display (plain text for CMD compatibility)"""
    target = session.target_minutes
    progress_pct = min(100, (elapsed_minutes / target) * 100) if target > 0 else 0

    # Create progress bar
    bar_width = 40
    filled = int((progress_pct / 100) * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)

    # Time display
    elapsed_str = f"{elapsed_minutes}/{target} min"

    # Overtime handling
    if elapsed_minutes >= target:
        status = "[yellow]⏰ Pomodoro complete![/yellow]"
        remaining_str = f"+{elapsed_minutes - target}m overtime"
    else:
        status = "[green]⏱️  Active[/green]"
        remaining_str = f"{remaining_minutes}m remaining"

    # Task info
    task_name = session.task_description or "Ad-hoc work"

    lines = [
        "[bold cyan]" + "=" * 60 + "[/bold cyan]",
        f"[bold cyan]CURRENT SESSION: {task_name}[/bold cyan]",
        "[bold cyan]" + "=" * 60 + "[/bold cyan]",
        ""
    ]

    if session.intent:
        intent_display = session.intent[:60] + "..." if len(session.intent) > 60 else session.intent
        lines.append(f"[dim]Intent:[/dim] {intent_display}")
        lines.append("")

    lines.extend([
        status,
        f"[cyan]{bar}[/cyan]",
        f"{elapsed_str} | {remaining_str}",
        "",
        "[dim]Press Ctrl+C for menu (stop/open resources/continue)[/dim]"
    ])

    return "\n".join(lines)


def display_session_complete(session: Session, elapsed_minutes: int):
    """Display session completion notification"""
    console.print("\n")
    console.print("[bold yellow]🔔 Pomodoro complete![/bold yellow]")
    console.print(f"Elapsed: {elapsed_minutes} minutes")
    console.print("\nOptions:")
    console.print("  [cyan]d[/cyan] Done - log session and stop")
    console.print("  [cyan]c[/cyan] Continue - keep working (extend 25min)")
    console.print("  [cyan]s[/cyan] Switch - log session and start new task")
    console.print("  [cyan]b[/cyan] Break - log session, take break")


def display_idle_warning(minutes_idle: int):
    """Display idle warning"""
    console.print("\n")
    panel = Panel(
        f"[yellow]No active session[/yellow]\nLast activity: {minutes_idle} minutes ago",
        box=box.ROUNDED,
        border_style="yellow",
        title="⚠️  Idle Warning"
    )
    console.print(panel)


def display_sleep_detected(gap_minutes: int):
    """Display sleep/wake detection message"""
    console.print("\n")
    panel = Panel(
        f"[yellow]Timer paused for {gap_minutes} minutes[/yellow]\n\nWere you away from your computer?",
        box=box.ROUNDED,
        border_style="yellow",
        title="Sleep/Wake Detected"
    )
    console.print(panel)


def display_task_list(tasks: List[Task]):
    """Display list of all tasks"""
    if not tasks:
        console.print("[dim]No tasks yet. Create one with 'pomodoro task add'[/dim]")
        return

    table = Table(title="All Tasks", show_header=True, box=box.ROUNDED)
    table.add_column("Quick Ref", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Source", style="dim")
    table.add_column("Last Worked", style="yellow")

    for task in tasks:
        last_worked = "Never"
        if task.last_worked:
            last_dt = datetime.fromisoformat(task.last_worked)
            delta = datetime.now() - last_dt

            if delta.days == 0:
                last_worked = "Today"
            elif delta.days == 1:
                last_worked = "Yesterday"
            else:
                last_worked = f"{delta.days}d ago"

        table.add_row(
            task.quick_ref or "-",
            task.name,
            task.source or "-",
            last_worked
        )

    console.print(table)


def display_report(content: str):
    """Display a report"""
    console.print("\n")
    console.print(Panel(content, box=box.ROUNDED, border_style="cyan"))

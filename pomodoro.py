#!/usr/bin/env python3
"""Pomodoro Task Tracker - Main CLI Entry Point"""

import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.live import Live

from src.session import session_manager
from src.tasks import task_manager
from src.reporter import reporter
from src.config import config
from src import ui


console = Console()


class PomodoroCLI:
    """Main CLI application"""

    def __init__(self):
        self.running = True
        self.last_idle_check = datetime.now()
        self.last_long_session_check = datetime.now()

    def run(self, args):
        """Main entry point"""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)

        if not hasattr(parsed_args, 'func'):
            # No command specified, run interactive mode
            self.interactive_mode()
        else:
            # Run the specified command
            parsed_args.func(parsed_args)

    def create_parser(self):
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            description='Pomodoro Task Tracker - ADHD-friendly time tracking',
            prog='pomodoro'
        )

        subparsers = parser.add_subparsers(title='commands', dest='command')

        # Session commands
        start_parser = subparsers.add_parser('start', help='Start new session')
        start_parser.set_defaults(func=self.cmd_start)

        stop_parser = subparsers.add_parser('stop', help='End current session')
        stop_parser.set_defaults(func=self.cmd_stop)

        status_parser = subparsers.add_parser('status', help='Show current timer')
        status_parser.set_defaults(func=self.cmd_status)

        extend_parser = subparsers.add_parser('extend', help='Extend current session')
        extend_parser.add_argument('minutes', type=int, nargs='?', default=25, help='Minutes to add')
        extend_parser.set_defaults(func=self.cmd_extend)

        break_parser = subparsers.add_parser('break', help='Log session and take break')
        break_parser.set_defaults(func=self.cmd_break)

        cancel_parser = subparsers.add_parser('cancel', help='Cancel current session')
        cancel_parser.set_defaults(func=self.cmd_cancel)

        # Task commands
        task_parser = subparsers.add_parser('task', help='Task management')
        task_subparsers = task_parser.add_subparsers(title='task commands', dest='task_command')

        task_list_parser = task_subparsers.add_parser('list', help='Show all tasks')
        task_list_parser.set_defaults(func=self.cmd_task_list)

        task_add_parser = task_subparsers.add_parser('add', help='Create new task')
        task_add_parser.set_defaults(func=self.cmd_task_add)

        task_show_parser = task_subparsers.add_parser('show', help='Show task details')
        task_show_parser.add_argument('ref', help='Task quick reference or ID')
        task_show_parser.set_defaults(func=self.cmd_task_show)

        task_search_parser = task_subparsers.add_parser('search', help='Search tasks')
        task_search_parser.add_argument('term', help='Search term')
        task_search_parser.set_defaults(func=self.cmd_task_search)

        # Report commands
        report_parser = subparsers.add_parser('report', help='Generate reports')
        report_subparsers = report_parser.add_subparsers(title='report commands', dest='report_command')

        report_today_parser = report_subparsers.add_parser('today', help='Today\'s summary')
        report_today_parser.set_defaults(func=self.cmd_report_today)

        report_week_parser = report_subparsers.add_parser('week', help='This week\'s summary')
        report_week_parser.set_defaults(func=self.cmd_report_week)

        report_task_parser = report_subparsers.add_parser('task', help='Task summary')
        report_task_parser.add_argument('ref', help='Task quick reference or ID')
        report_task_parser.set_defaults(func=self.cmd_report_task)

        # Config command
        config_parser = subparsers.add_parser('config', help='Show configuration')
        config_parser.set_defaults(func=self.cmd_config)

        return parser

    # Command implementations

    def cmd_start(self, args):
        """Start a new session"""
        if session_manager.current_session:
            ui.print_error("A session is already active. Stop it first with 'pomodoro stop'")
            return

        # Get recent tasks
        recent_tasks = task_manager.get_recent_tasks(10)

        # Prompt for task selection
        task_idx = ui.prompt_task_selection(recent_tasks)

        task = None
        if task_idx == -1:
            # Create new task
            task_data = ui.prompt_create_task()
            task = task_manager.create_task(**task_data)
            ui.print_success(f"Task created: {task.display_name()}")

            # Add resources
            ui.prompt_add_resources(task.id)

        elif task_idx is not None:
            task = recent_tasks[task_idx]

        # Show task details if selected
        if task:
            resources = task_manager.get_task_resources(task.id)
            recent_sessions = task_manager.get_task_sessions(task.id, limit=3)
            ui.display_task_details(task, resources, recent_sessions)

        # Get intent
        intent = Prompt.ask("\nWhat are you trying to accomplish?", default="")

        # Get working directory
        default_dir = str(Path.cwd())
        working_dir = None

        if config.show_file_tracking:
            console.print(f"\nWorking directory: [cyan]{default_dir}[/cyan]")
            if Confirm.ask("Track files in this directory?", default=True):
                working_dir = default_dir

        # Start session
        session = session_manager.start_session(
            task=task,
            intent=intent or None,
            working_directory=working_dir
        )

        target_end = datetime.now() + timedelta(minutes=session.target_minutes)
        ui.print_success(
            f"Session started at {datetime.now().strftime('%H:%M')}\n"
            f"   Target: {session.target_minutes} minutes (break at {target_end.strftime('%H:%M')})"
        )

        if working_dir:
            ui.print_info(f"Tracking: {working_dir}")

        # Enter live display mode
        self.live_session_display()

    def cmd_stop(self, args):
        """Stop current session"""
        if not session_manager.current_session:
            ui.print_error("No active session")
            return

        # Get outcome
        outcome = Prompt.ask("\nWhat did you actually accomplish?", default="")

        # Get modified files
        modified_files = session_manager.get_modified_files()
        files_to_log = None

        if modified_files:
            files_to_log = ui.prompt_file_selection(modified_files)

        # Stop session
        session = session_manager.stop_session(
            outcome=outcome or None,
            files_to_log=files_to_log
        )

        duration = session.duration_minutes - session.paused_duration
        ui.print_success(f"Session logged: {duration} minutes")

        if session.task_description:
            console.print(f"   Task: {session.task_description}")

        if files_to_log:
            file_count = len(files_to_log.split(','))
            console.print(f"   Files: {file_count} file(s) logged")

    def cmd_status(self, args):
        """Show current session status"""
        if not session_manager.current_session:
            ui.print_info("No active session")

            # Show last session time
            last_session = session_manager.get_last_session_time()
            if last_session:
                delta = datetime.now() - last_session
                minutes_ago = int(delta.total_seconds() / 60)
                console.print(f"Last session ended {minutes_ago} minutes ago")

            return

        # Display current session
        elapsed = session_manager.get_elapsed_minutes()
        remaining = session_manager.get_remaining_minutes()

        panel = ui.create_timer_display(
            session_manager.current_session,
            elapsed,
            remaining
        )

        console.print(panel)

    def cmd_extend(self, args):
        """Extend current session"""
        if not session_manager.current_session:
            ui.print_error("No active session to extend")
            return

        session_manager.extend_session(args.minutes)
        ui.print_success(f"Extended by {args.minutes} minutes (new target: {session_manager.current_session.target_minutes}m)")

    def cmd_break(self, args):
        """Take a break (stop session)"""
        if not session_manager.current_session:
            ui.print_error("No active session")
            return

        self.cmd_stop(args)
        ui.print_info("Enjoy your break!")

    def cmd_cancel(self, args):
        """Cancel current session"""
        if not session_manager.current_session:
            ui.print_error("No active session")
            return

        if Confirm.ask("Cancel current session without logging?", default=False):
            session_manager.cancel_session()
            ui.print_success("Session cancelled")

    def cmd_task_list(self, args):
        """List all tasks"""
        tasks = task_manager.get_all_tasks()
        ui.display_task_list(tasks)

    def cmd_task_add(self, args):
        """Add new task"""
        task_data = ui.prompt_create_task()
        task = task_manager.create_task(**task_data)
        ui.print_success(f"Task created: {task.display_name()}")

        ui.prompt_add_resources(task.id)

    def cmd_task_show(self, args):
        """Show task details"""
        # Try to find task by quick_ref or ID
        task = task_manager.get_task_by_quick_ref(args.ref)

        if not task:
            try:
                task_id = int(args.ref)
                task = task_manager.get_task(task_id)
            except ValueError:
                pass

        if not task:
            ui.print_error(f"Task not found: {args.ref}")
            return

        resources = task_manager.get_task_resources(task.id)
        recent_sessions = task_manager.get_task_sessions(task.id, limit=5)

        ui.display_task_details(task, resources, recent_sessions)

    def cmd_task_search(self, args):
        """Search tasks"""
        tasks = task_manager.search_tasks(args.term)

        if not tasks:
            ui.print_info(f"No tasks found matching '{args.term}'")
            return

        ui.display_task_list(tasks)

    def cmd_report_today(self, args):
        """Show today's report"""
        report = reporter.generate_daily_report()
        ui.display_report(report)

        if Confirm.ask("\nExport report?", default=False):
            path = reporter.export_report(report)
            ui.print_success(f"Report saved: {path}")

    def cmd_report_week(self, args):
        """Show weekly report"""
        report = reporter.generate_weekly_report()
        ui.display_report(report)

        if Confirm.ask("\nExport report?", default=False):
            path = reporter.export_report(report)
            ui.print_success(f"Report saved: {path}")

    def cmd_report_task(self, args):
        """Show task report"""
        # Try to find task
        task = task_manager.get_task_by_quick_ref(args.ref)

        if not task:
            try:
                task_id = int(args.ref)
                task = task_manager.get_task(task_id)
            except ValueError:
                pass

        if not task:
            ui.print_error(f"Task not found: {args.ref}")
            return

        report = reporter.generate_task_report(task.id)
        ui.display_report(report)

        if Confirm.ask("\nExport report?", default=False):
            path = reporter.export_report(report)
            ui.print_success(f"Report saved: {path}")

    def cmd_config(self, args):
        """Show configuration"""
        console.print("[bold]Configuration:[/bold]")
        console.print(f"Database: {config.db_path}")
        console.print(f"OneDrive: {config.onedrive_path}")
        console.print(f"Work hours: {config.work_start.strftime('%H:%M')} - {config.work_end.strftime('%H:%M')}")
        console.print(f"Lunch: {config.lunch_start.strftime('%H:%M')} - {config.lunch_end.strftime('%H:%M')}")
        console.print(f"Default pomodoro: {config.default_pomodoro_minutes} minutes")
        console.print(f"Idle warning: {config.idle_warning_minutes} minutes")

    # Interactive mode and live display

    def interactive_mode(self):
        """Run in interactive mode with live display"""
        console.print("[bold cyan]Pomodoro Task Tracker[/bold cyan]")
        console.print("Type 'help' for commands, 'start' to begin a session, 'quit' to exit\n")

        while self.running:
            try:
                # If there's an active session, show live display
                if session_manager.current_session:
                    self.live_session_display()
                else:
                    # No active session, check for idle
                    self.check_idle_warning()

                    # Wait for command
                    command = Prompt.ask("\n[bold]pomodoro[/bold]").strip()

                    if command.lower() in ['quit', 'exit', 'q']:
                        self.running = False
                        break

                    if command.lower() in ['help', 'h', '?']:
                        self.show_help()
                        continue

                    # Parse and run command
                    if command:
                        self.run(command.split())

            except KeyboardInterrupt:
                console.print("\n")
                if Confirm.ask("Exit?", default=False):
                    self.running = False
            except Exception as e:
                ui.print_error(f"Error: {e}")

    def live_session_display(self):
        """Display live session timer"""
        if not session_manager.current_session:
            return

        try:
            with Live(console=console, refresh_per_second=1) as live:
                while session_manager.current_session:
                    # Check for sleep gap
                    gap = session_manager.check_for_sleep_gap()
                    if gap and gap > config.sleep_gap_threshold_minutes:
                        live.stop()
                        ui.display_sleep_detected(gap)

                        if Confirm.ask("Still working? (No = stop session)", default=True):
                            # Pause this time
                            session_manager.pause_session(gap)
                            ui.print_info(f"Paused {gap} minutes from session time")
                        else:
                            # Stop session
                            self.cmd_stop(argparse.Namespace())
                            return

                        live.start()

                    # Update tick
                    session_manager.update_tick()

                    # Get current metrics
                    elapsed = session_manager.get_elapsed_minutes()
                    remaining = session_manager.get_remaining_minutes()

                    # Update display
                    panel = ui.create_timer_display(
                        session_manager.current_session,
                        elapsed,
                        remaining
                    )

                    live.update(panel)

                    # Check if pomodoro complete
                    if session_manager.is_overtime() and elapsed == session_manager.current_session.target_minutes:
                        # Just hit the target
                        live.stop()
                        ui.display_session_complete(session_manager.current_session, elapsed)

                        choice = Prompt.ask("Select", choices=['d', 'c', 's', 'b']).lower()

                        if choice == 'd':
                            self.cmd_stop(argparse.Namespace())
                            return
                        elif choice == 'c':
                            self.cmd_extend(argparse.Namespace(minutes=25))
                            live.start()
                        elif choice == 's':
                            self.cmd_stop(argparse.Namespace())
                            self.cmd_start(argparse.Namespace())
                            return
                        elif choice == 'b':
                            self.cmd_break(argparse.Namespace())
                            return

                    # Check for long session (every 2 hours)
                    if elapsed > 0 and elapsed % 120 == 0:
                        now = datetime.now()
                        if (now - self.last_long_session_check).total_seconds() > 300:  # Check at most every 5 min
                            live.stop()
                            ui.print_warning(f"Long session: {elapsed} minutes. Consider taking a break!")
                            self.last_long_session_check = now

                            if not Confirm.ask("Continue session?", default=True):
                                self.cmd_stop(argparse.Namespace())
                                return

                            live.start()

                    time.sleep(1)

        except KeyboardInterrupt:
            console.print("\n")
            if Confirm.ask("Stop current session?", default=False):
                self.cmd_stop(argparse.Namespace())

    def check_idle_warning(self):
        """Check if idle warning should be shown"""
        now = datetime.now()

        # Only check during work hours
        if not config.is_work_hours(now.time()):
            return

        # Check if enough time has passed since last check
        if (now - self.last_idle_check).total_seconds() < 60:  # Check at most once per minute
            return

        self.last_idle_check = now

        # Get last session end time
        last_session = session_manager.get_last_session_time()
        if not last_session:
            return

        # Calculate idle time
        idle_delta = now - last_session
        idle_minutes = int(idle_delta.total_seconds() / 60)

        if idle_minutes >= config.idle_warning_minutes:
            ui.display_idle_warning(idle_minutes)

            choice = Prompt.ask("Start a session?", choices=['y', 'n', 's'], default='n').lower()

            if choice == 'y':
                self.cmd_start(argparse.Namespace())
            elif choice == 's':
                # Snooze for 30 minutes
                self.last_idle_check = now + timedelta(minutes=30)
                ui.print_info("Snoozed for 30 minutes")

    def show_help(self):
        """Show help message"""
        console.print("""
[bold]Session Management:[/bold]
  start              Start new session
  stop               End current session
  status             Show current timer
  extend [minutes]   Extend current session (default +25)
  break              Log session and take break
  cancel             Cancel current session (don't log)

[bold]Task Management:[/bold]
  task list          Show all tasks
  task add           Create new task (interactive)
  task show <ref>    Show task details and history
  task search <term> Search tasks

[bold]Reporting:[/bold]
  report today       Today's work summary
  report week        This week's summary
  report task <ref>  All work on specific task

[bold]Other:[/bold]
  config             Show current configuration
  help               Show this help
  quit               Exit
        """)


def main():
    """Main entry point"""
    try:
        cli = PomodoroCLI()
        cli.run(sys.argv[1:])
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted[/dim]")
        sys.exit(0)
    except Exception as e:
        ui.print_error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

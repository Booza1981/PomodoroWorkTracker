# Pomodoro Task Tracker

A lightweight Python CLI tool for ADHD-friendly time tracking, task management, and productivity reporting. Track work sessions with intent/outcome logging, manage tasks with resources, and generate weekly reports.

## Features

- **25-minute Pomodoro sessions** with manual controls (start, stop, extend, break)
- **Task management** with Microsoft Planner/To Do URL support
- **File tracking** during sessions to see what you worked on
- **Sleep/wake detection** with automatic pause and resume prompts
- **Idle warnings** when no session is active during work hours
- **Weekly reporting** with task summaries, intent/outcome highlights, and file tracking
- **SQLite database** stored in OneDrive for cross-machine sync
- **Rich terminal UI** with live timer display and progress bars

## Requirements

- Windows 10/11
- Python 3.10+
- OneDrive (for database sync)

## Installation

1. **Clone or download** this repository:
   ```bash
   cd C:\path\to\your\projects
   git clone <repo-url> PomodoroWorkTracker
   cd PomodoroWorkTracker
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure OneDrive path** (optional):

   Copy `.env.example` to `.env` and edit if needed:
   ```bash
   copy .env.example .env
   notepad .env
   ```

   The tool will automatically detect your OneDrive path from environment variables (`%OneDriveCommercial%` or `%OneDrive%`). Only customize if you have a non-standard setup.

4. **Test the installation**:
   ```bash
   python pomodoro.py status
   ```

   You should see "No active session".

## Setup Auto-Start (Optional)

To automatically start the Pomodoro tracker when you log in:

1. **Run the setup script**:
   ```bash
   python setup_scheduler.py
   ```

2. This will create a Windows Task Scheduler task that launches the tracker on login.

3. To uninstall later:
   ```bash
   schtasks /delete /tn "PomodoroTaskTracker" /f
   ```

## Quick Start

### Starting Your First Session

```bash
python pomodoro.py start
```

This will:
1. Show you recent tasks or let you create a new one
2. Ask what you're trying to accomplish (intent)
3. Optionally track files in your working directory
4. Start a 25-minute timer with live display

### Stopping a Session

When the timer completes, you'll be prompted to:
- **Done** - Log session and stop
- **Continue** - Extend by 25 minutes
- **Switch** - Log and start a new task
- **Break** - Log and take a break

You can also manually stop:
```bash
python pomodoro.py stop
```

### Interactive Mode

Run without arguments for interactive mode:
```bash
python pomodoro.py
```

Type commands like `start`, `stop`, `status`, etc. Type `help` for all commands.

## Usage

### Session Commands

```bash
# Start a new session
python pomodoro.py start

# Check current session status
python pomodoro.py status

# Stop current session
# (Or press Ctrl+C during live display)
python pomodoro.py stop

# Extend current session by 25 minutes (or specify amount)
python pomodoro.py extend
python pomodoro.py extend 15

# Cancel without logging
python pomodoro.py cancel
```

**Note**: The `stop` command is most useful when:
- Running from a second terminal while the live timer is in another terminal
- Using the tool in scripts or automation
- You prefer command-line style over interactive mode

During an active session with live display, press `Ctrl+C` to stop.

### Task Commands

```bash
# List all tasks
python pomodoro.py task list

# Add a new task (interactive)
python pomodoro.py task add

# Show task details and history
python pomodoro.py task show PLNR-1234
python pomodoro.py task show 1

# Search tasks
python pomodoro.py task search "budget review"
```

### Reporting Commands

```bash
# Today's summary
python pomodoro.py report today

# This week's summary
python pomodoro.py report week

# Specific task history
python pomodoro.py report task PLNR-1234
```

### Configuration

```bash
# Show current configuration
python pomodoro.py config
```

## Configuration File

Edit `.env` to customize:

```env
# OneDrive location (auto-detected if not specified)
# ONEDRIVE_PATH=C:\Users\username\OneDrive - Company

# Work hours (24-hour format)
WORK_START=09:00
WORK_END=17:00
LUNCH_START=12:00
LUNCH_END=13:00

# Session defaults
DEFAULT_POMODORO_MINUTES=25
IDLE_WARNING_MINUTES=30

# Behavior
AUTO_PAUSE_ON_SLEEP=true
SHOW_FILE_TRACKING=true
```

## Workflow Examples

### Example 1: Working on a Planner Task

```bash
# Start session
python pomodoro.py start

> Recent tasks:
>   1. Q4 Budget Review (PLNR-1234) - last: 2 days ago
>   2. Email stakeholders - last: today
>   [n] New task
>   [Enter] No task (ad-hoc work)
>
> Select: 1
>
> Task: Q4 Budget Review (PLNR-1234)
> Link: https://tasks.office.com/.../abc123
> Resources:
>   📁 C:\Budget\2024\
>
> What are you trying to accomplish?: Final review before submission
>
> Working directory: C:\Budget\2024
> Track files? [Y/n]: y
>
> ✓ Session started at 10:15
>   Target: 25 minutes (break at 10:40)
>   Tracking: C:\Budget\2024

[Live timer display shows progress]

# When done
python pomodoro.py stop

> What did you actually accomplish?: Finished review, found formatting issue, fixed it
>
> Files modified during session:
>   1. budget_summary_2024.xlsx (10:23)
>   2. revenue_model_v3.xlsx (10:35)
>
> Select files to log [1,2 or 'all']: all
>
> ✓ Session logged: 47 minutes
>   Task: Q4 Budget Review (PLNR-1234)
>   Files: 2 file(s) logged
```

### Example 2: Weekly Report

```bash
python pomodoro.py report week

> Week of December 16 - December 22, 2024
> ========================================
> Total: 18h 35m across 24 sessions
>
> By Task:
> ========================================
>
> Q4 Budget Review (PLNR-1234) - 4h 35m (6 sessions)
>   Link: https://tasks.office.com/.../abc123
>   Intent → Outcome highlights:
>     • Final review → Completed, found/fixed formatting issue
>     • Revenue projections → Updated with Q3 actuals
>   Files: budget_summary_2024.xlsx (3x), revenue_model_v3.xlsx (2x)
>
> Export report? [y/N]: y
> ✓ Report saved: C:\Users\...\OneDrive\PomodoroTracker\Reports\pomodoro_report_2024-12-22_143022.md
```

## Features Explained

### Sleep/Wake Detection

When you lock your computer or it goes to sleep, the timer automatically detects the gap:

```
> Sleep/Wake Detected
> Timer paused for 45 minutes
> Were you away from your computer?
>
> Still working? (No = stop session) [Y/n]:
```

If you confirm, the paused time is subtracted from your session duration.

### Idle Warnings

During work hours (9am-5pm, excluding lunch), if no session is active for 30 minutes:

```
> ⚠️ No active session
> Last activity: 35 minutes ago
>
> Start a session? [Y/n/s=snooze 30min]:
```

### File Tracking

When you start a session with file tracking enabled:
1. The tool snapshots all file modification times in the directory (recursive)
2. When you stop the session, it shows which files changed
3. You can select which files to log with the session

This helps you remember what you actually worked on and creates a record for reports.

## Database

- **Location**: `%OneDrive%\PomodoroTracker\pomodoro.db` (or `%OneDriveCommercial%`)
  - If OneDrive not detected, falls back to `%USERPROFILE%\PomodoroTracker\pomodoro.db`
  - Check actual location with `python pomodoro.py config`
- **Format**: SQLite database
- **Size**: Typically <10MB (months of data)
- **Sync**: Automatically syncs via OneDrive across machines (if in OneDrive)
- **Backup**: Included in OneDrive backups

## Troubleshooting

### Database Locked Error

If you see "Database locked" errors:
- This happens when OneDrive is actively syncing
- The tool automatically retries with exponential backoff
- If it persists, wait a moment and try again

### OneDrive Not Detected

If OneDrive path isn't auto-detected:
1. Check that `%OneDrive%` or `%OneDriveCommercial%` environment variables are set
2. Manually set `ONEDRIVE_PATH` in `.env`

### Task Scheduler Not Working

If auto-start doesn't work:
1. Open Task Scheduler (taskschd.msc)
2. Find "PomodoroTaskTracker" task
3. Check that the Python path and script path are correct
4. Run `setup_scheduler.py` again

## Project Structure

```
PomodoroWorkTracker/
├── pomodoro.py              # Main CLI entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Configuration template
├── setup_scheduler.py      # Task Scheduler setup
├── setup_scheduler.xml     # Task Scheduler template
├── README.md               # This file
├── SPEC.md                 # Technical specification
└── src/
    ├── config.py           # Configuration management
    ├── database.py         # Database and schema
    ├── models.py           # Data models
    ├── session.py          # Session management
    ├── tasks.py            # Task CRUD operations
    ├── file_tracker.py     # File change detection
    ├── reporter.py         # Report generation
    └── ui.py               # Rich UI components
```

## Tips for ADHD Users

1. **Use task resources**: Store file paths, URLs, and notes with each task so you don't forget where things are

2. **Write detailed intents**: When starting a session, be specific about what you're trying to do. This helps you stay focused and makes reports more useful.

3. **Don't fight the timer**: If you're in flow and the 25 minutes is up, just hit "continue" to extend. The tool is here to help, not interrupt.

4. **Review weekly reports**: Use `report week` every Friday to see what you actually accomplished. It's often more than you think!

5. **Use quick references**: Create short codes like "PROJ-123" for tasks so you can quickly find them

6. **Let idle warnings help**: The 30-minute idle check is a gentle nudge to either start working or be intentional about taking a break

## License

See SPEC.md for project details and requirements.

## Support

For issues, questions, or feature requests, please see the repository issues page.

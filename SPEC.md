# Pomodoro Task Tracker - Technical Specification

## Purpose
A lightweight Python CLI tool for ADHD-friendly time tracking, task management, and productivity reporting. Tracks work sessions with intent/outcome logging, manages tasks with resources, and generates weekly reports.

## Core Functionality

### 1. Session Management
- **Default session**: 25 minutes (pomodoro standard)
- **Manual controls**: Start, stop, extend, break
- **Auto-pause**: Detect system sleep/lock, pause timer
- **Auto-resume**: Resume timer on wake (ask user to confirm)
- **Idle detection**: Prompt if no active session for 30min during work hours (9am-5pm, skip 12-1pm)
- **Session logging**: Capture intent (start), outcome (end), files modified during session

### 2. Task Management
- **Task types**: Planner tasks (URL), Microsoft To Do tasks (URL), or local/ad-hoc
- **Quick reference**: Optional short codes (e.g., "PLNR-1234")
- **Task resources**: Store file paths, folder paths, URLs, notes per task
- **Task selection**: Show recent tasks on start, autocomplete from history
- **Task context**: Display resources, notes, and recent work when selecting a task

### 3. File Tracking
- **Monitor working directory**: Snapshot file mtimes at session start
- **Detect changes**: At session end, show modified files in directory
- **Selective logging**: Let user choose which files to log with session
- **Storage**: Store file paths with each session

### 4. Data Storage
- **SQLite database**: Single .db file in configured OneDrive location
- **Tables**: tasks, task_resources, sessions
- **OneDrive sync**: Database in OneDrive folder for cross-machine sync

### 5. Reporting
- **Weekly report**: Show all work done, grouped by task, with time totals
- **Task summary**: Show all sessions for a specific task
- **Daily summary**: Quick view of today's work
- **Export**: Generate report as markdown/text file

### 6. User Interface
- **Terminal-based**: Single terminal window that stays open
- **Rich formatting**: Use `rich` library for colors, progress bars, tables
- **Live display**: Show current timer, task, elapsed time
- **Prompts**: Interactive prompts for task selection, file selection
- **Commands**: Simple commands (start, stop, status, report, task, etc.)

## Technical Requirements

### Platform
- Windows 10/11
- Python 3.10+
- No admin rights needed
- Minimal dependencies (sqlite3, rich, only standard library otherwise)

### Configuration
- **.env file**: Store OneDrive path
- **Environment variable**: Read `%OneDrive%` or `%OneDriveCommercial%` for default
- **Work hours**: Configurable in .env (default 9am-5pm)
- **Lunch break**: Configurable in .env (default 12pm-1pm)

### Auto-start Behavior
- **Task Scheduler**: Auto-start on user login
- **Desktop shortcut**: Manual launch option
- **Auto-reopen**: If closed during work hours, relaunch via scheduled task (check every 15min)
- **Background process**: Runs as foreground terminal window (not hidden)

### Sleep/Lock Handling
- **Detect sleep**: Use Windows API to detect system suspend
- **Pause timer**: Automatically pause on sleep/lock
- **Resume prompt**: On wake, ask "Still working on [task]? Resume/Stop/Switch"

## Database Schema

```sql
CREATE TABLE tasks (
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

CREATE TABLE task_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    type TEXT CHECK(type IN ('file', 'folder', 'url', 'note')),
    value TEXT NOT NULL,
    description TEXT,
    created_date TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE TABLE sessions (
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

CREATE INDEX idx_sessions_start ON sessions(start_time);
CREATE INDEX idx_sessions_task ON sessions(task_id);
CREATE INDEX idx_tasks_last_worked ON tasks(last_worked);
```

## User Flows

### Starting a Session

```
> pomodoro start

Recent tasks (by last worked):
  1. Q4 Budget Review (PLNR-1234) - last: 2 days ago
  2. Email stakeholders - last: today
  3. Data cleanup (TODO-789) - last: 3 days ago
  [n] New task
  [Enter] No task (ad-hoc work)

Select [1-3, n, Enter]: 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Q4 Budget Review (PLNR-1234)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 https://tasks.office.com/.../abc123

Resources:
  📁 C:\Budget\2024\
  📁 C:\Finance\Models\
  🔗 https://sharepoint.../dashboard
  💡 Always check assumptions tab in master file

Recent work:
  • 2 days ago: Updating revenue projections (47m)
  • 3 days ago: Initial model review (52m)

What are you trying to accomplish?: 
> Final review before submission to CFO

Working directory: C:\Budget\2024
Track files in this directory? [Y/n]: y

🍅 Session started at 10:15
   Target: 25 minutes (break at 10:40)
   Tracking: C:\Budget\2024

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️  Q4 Budget Review (PLNR-1234)
   Intent: Final review before submission to CFO
   ████████████░░░░░░░░  18/25 min
   Elapsed: 18:23
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### At 25 Minutes

```
🔔 Pomodoro complete!

Options:
  [d] Done - log session and stop
  [c] Continue - keep working (extend 25min)
  [s] Switch - log session and start new task
  [b] Break - log session, take break

Select [d/c/s/b]: c

⏱️  Extended to 50 minutes
   ████░░░░░░░░░░░░░░░░  28/50 min
```

### Ending a Session

```
> pomodoro stop

What did you actually accomplish?:
> Finished review, found formatting issue in summary table, fixed it

Files modified during session:
  1. budget_summary_2024.xlsx (10:23)
  2. revenue_model_v3.xlsx (10:35)
  3. ~temp_calc.xlsx (10:28)
  
Select files to log [1,2 or 'all' or Enter for all]: 1,2

✅ Session logged: 47 minutes
   Task: Q4 Budget Review (PLNR-1234)
   Files: budget_summary_2024.xlsx, revenue_model_v3.xlsx
```

### Creating New Task

```
> pomodoro start
Select: n

Task name: Client onboarding documentation
Quick reference (optional): CLI-001
Source [planner/todo/local]: planner
Planner URL (or Enter to skip): https://tasks.office.com/.../xyz789

Add resources? [y/N]: y

Resource type [file/folder/url/note/done]: folder
Path: C:\Projects\ClientOnboarding\
Resource type: url
URL: https://wiki.company.com/onboarding
Resource type: note
Note: Use template v2.1, not v2.0
Resource type: done

✅ Task created: Client onboarding documentation (CLI-001)
```

### Idle Detection

```
[No active session for 35 minutes during work hours]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  No active session
   Last activity: 35 minutes ago
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Start a session? [Y/n/s=snooze 30min]: 
```

### Weekly Report

```
> pomodoro report week

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Week of December 16-22, 2024
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total: 18h 35m across 24 sessions

By Task:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Q4 Budget Review (PLNR-1234) - 4h 35m (6 sessions)
  🔗 https://tasks.office.com/.../abc123
  Intent → Outcome highlights:
    • Final review → Completed, found/fixed formatting issue
    • Revenue projections → Updated with Q3 actuals
  Files: budget_summary_2024.xlsx (3x), revenue_model_v3.xlsx (2x)

Client Onboarding (CLI-001) - 3h 20m (4 sessions)
  🔗 https://tasks.office.com/.../xyz789
  Intent → Outcome highlights:
    • Draft documentation → Completed sections 1-3
    • Review feedback → Incorporated all comments

Email & Admin - 2h 15m (8 sessions)
  Ad-hoc work, no specific task

Team Meeting Notes - 1h 45m (3 sessions)
  ...

Export this report? [y/N]: y
📄 Saved to: C:\Users\...\OneDrive\pomodoro_report_2024-12-22.md
```

## Commands Reference

```
Session Management:
  pomodoro start              Start new session
  pomodoro stop               End current session
  pomodoro status             Show current timer
  pomodoro extend [minutes]   Extend current session (default +25)
  pomodoro break              Log session and take break
  pomodoro cancel             Cancel current session (don't log)

Task Management:
  pomodoro task list          Show all tasks
  pomodoro task add           Create new task (interactive)
  pomodoro task edit <ref>    Edit task details/resources
  pomodoro task show <ref>    Show task details and history
  pomodoro task search <term> Search tasks

Reporting:
  pomodoro report today       Today's work summary
  pomodoro report week        This week's summary
  pomodoro report task <ref>  All work on specific task
  pomodoro report export      Export report to file

Configuration:
  pomodoro config             Show current configuration
  pomodoro config set <key> <value>  Update setting
```

## Configuration File (.env)

```
# OneDrive location (defaults to %OneDriveCommercial% or %OneDrive%)
ONEDRIVE_PATH=C:\Users\username\OneDrive - Company

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

## Error Handling & Edge Cases

1. **Database locked**: Retry with exponential backoff, warn if OneDrive sync issue
2. **Session interrupted**: If program crashes, mark last active session as cancelled on next start
3. **Invalid URLs**: Validate Microsoft URLs, warn if can't parse task ID
4. **Missing directories**: Warn if working directory doesn't exist, don't fail
5. **Clock changes**: Handle daylight savings, system time changes gracefully
6. **Long sessions**: Auto-prompt every 2 hours if session still active

## Success Criteria

- Launches in <2 seconds
- Session start/stop takes <5 seconds
- Database file stays <10MB (will be months of data)
- No dependencies requiring compilation
- Works offline (except URL validation)
- Survives system sleep/wake cycle
- Clear, actionable error messages

---

## Implementation Notes for Claude Code

- Use SQLite for storage with proper connection handling
- Use Rich library for terminal UI with live display
- Implement as modular Python package or single well-structured script
- Include comprehensive error handling and logging
- Create Task Scheduler XML template for auto-start setup
- Keep dependencies minimal (sqlite3, rich, python-dotenv, standard library)
- Code should be well-commented and maintainable
- Include README with setup instructions

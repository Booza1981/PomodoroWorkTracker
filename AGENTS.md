# Repository Guidelines

## Project Structure & Module Organization
`pomodoro.py` is the CLI entry point. Core logic lives in `src/` (session flow, tasks, reporting, database, UI). Configuration defaults are in `.env.example`, and Windows auto-start helpers are `setup_scheduler.py` and `setup_scheduler.xml`. Runtime data is a local SQLite database stored under OneDrive (not in this repo).

## Build, Test, and Development Commands
- `pip install -r requirements.txt` — install Python dependencies.
- `python pomodoro.py` — launch interactive CLI mode.
- `python pomodoro.py status` — quick smoke check for a clean install.
- `python pomodoro.py report week` — verify reporting output.
- `python setup_scheduler.py` — create the Windows Task Scheduler entry.

## Coding Style & Naming Conventions
Use standard Python conventions: 4-space indentation, snake_case for functions/modules, CapWords for classes, and UPPER_SNAKE_CASE for constants. Keep CLI messages concise and user-facing prompts friendly. Prefer small, single-purpose functions in `src/` and route user commands through `pomodoro.py`.

## Testing Guidelines
There is no automated test suite yet. Validate changes with manual smoke checks:
- Start/stop a session: `python pomodoro.py start` then `python pomodoro.py stop`
- Verify status and reports: `python pomodoro.py status`, `python pomodoro.py report week`
If you add tests in the future, document how to run them here.

## Commit & Pull Request Guidelines
Commit messages follow an imperative, present-tense style (e.g., “Add notification…”, “Refactor resource opening…”). For PRs, include:
- A short description of the change and motivation
- Any new commands or config changes (`.env` keys, scheduler setup)
- Sample CLI output or screenshots when UI/UX changes
- Links to relevant issues or tasks when applicable

## Configuration & Data Handling
Keep `.env` local and do not commit user data or database files. The SQLite database lives under OneDrive by default; use `python pomodoro.py config` to confirm the active paths when debugging.

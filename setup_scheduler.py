#!/usr/bin/env python3
"""Setup Task Scheduler for auto-start on Windows"""

import sys
import os
import subprocess
from pathlib import Path


def setup_task_scheduler():
    """Setup Windows Task Scheduler to auto-start Pomodoro tracker"""

    # Get paths
    script_dir = Path(__file__).parent.absolute()
    pomodoro_script = script_dir / "pomodoro.py"
    xml_template = script_dir / "setup_scheduler.xml"

    # Find Python executable
    python_exe = sys.executable

    print("Pomodoro Task Tracker - Task Scheduler Setup")
    print("=" * 60)
    print(f"Python: {python_exe}")
    print(f"Script: {pomodoro_script}")
    print()

    # Read XML template
    with open(xml_template, 'r', encoding='utf-16') as f:
        xml_content = f.read()

    # Replace placeholders
    xml_content = xml_content.replace('CMD_PLACEHOLDER', python_exe)
    xml_content = xml_content.replace('ARG_PLACEHOLDER', str(pomodoro_script))
    xml_content = xml_content.replace('WORKDIR_PLACEHOLDER', str(script_dir))

    # Write configured XML
    output_xml = script_dir / "pomodoro_task.xml"
    with open(output_xml, 'w', encoding='utf-16') as f:
        f.write(xml_content)

    print("Created task configuration file.")
    print()
    print("To install the scheduled task, run this command in PowerShell or CMD:")
    print()
    print(f'  schtasks /create /tn "PomodoroTaskTracker" /xml "{output_xml}" /f')
    print()
    print("To uninstall later:")
    print()
    print('  schtasks /delete /tn "PomodoroTaskTracker" /f')
    print()
    print("Note: The task will start Pomodoro tracker automatically when you log in.")
    print("=" * 60)

    # Try to install automatically
    try:
        result = subprocess.run(
            ['schtasks', '/create', '/tn', 'PomodoroTaskTracker', '/xml', str(output_xml), '/f'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print()
            print("✓ Task successfully installed!")
            print("  The Pomodoro tracker will now start automatically when you log in.")
        else:
            print()
            print("Note: Automatic installation failed. Please run the command above manually.")
            if result.stderr:
                print(f"Error: {result.stderr}")
    except Exception as e:
        print()
        print("Note: Automatic installation not available. Please run the command above manually.")
        print(f"Details: {e}")


if __name__ == '__main__':
    setup_task_scheduler()

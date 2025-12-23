"""File tracking for detecting changes during work sessions"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class FileTracker:
    """Tracks file modifications in a directory during a session"""

    def __init__(self, directory: Optional[str] = None):
        """
        Initialize file tracker

        Args:
            directory: Directory to track (defaults to current directory)
        """
        self.directory = Path(directory) if directory else Path.cwd()
        self.snapshot: Dict[str, float] = {}
        self.start_time: Optional[datetime] = None

    def take_snapshot(self):
        """Take a snapshot of all file modification times in the directory (recursive)"""
        self.snapshot = {}
        self.start_time = datetime.now()

        if not self.directory.exists():
            return

        try:
            for root, dirs, files in os.walk(self.directory):
                # Skip hidden directories and common non-work directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', '.git']]

                for file in files:
                    # Skip hidden files and temp files
                    if file.startswith('.') or file.startswith('~'):
                        continue

                    file_path = Path(root) / file
                    try:
                        stat = file_path.stat()
                        # Store relative path and mtime
                        rel_path = file_path.relative_to(self.directory)
                        self.snapshot[str(rel_path)] = stat.st_mtime
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
        except (OSError, PermissionError):
            # Can't access directory
            pass

    def get_modified_files(self) -> List[Dict[str, any]]:
        """
        Get list of files modified since snapshot

        Returns:
            List of dicts with keys: 'path', 'rel_path', 'modified_time'
        """
        if not self.snapshot or not self.start_time:
            return []

        modified = []

        if not self.directory.exists():
            return modified

        try:
            for root, dirs, files in os.walk(self.directory):
                # Skip same directories as in snapshot
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', '.git']]

                for file in files:
                    if file.startswith('.') or file.startswith('~'):
                        continue

                    file_path = Path(root) / file
                    try:
                        stat = file_path.stat()
                        rel_path = str(file_path.relative_to(self.directory))

                        # Check if file is new or modified
                        is_new = rel_path not in self.snapshot
                        is_modified = (
                            rel_path in self.snapshot and
                            stat.st_mtime > self.snapshot[rel_path]
                        )

                        if is_new or is_modified:
                            modified.append({
                                'path': str(file_path),
                                'rel_path': rel_path,
                                'modified_time': datetime.fromtimestamp(stat.st_mtime)
                            })
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass

        # Sort by modification time
        modified.sort(key=lambda x: x['modified_time'])
        return modified

    def format_file_list(self, files: List[Dict[str, any]], max_display: int = 20) -> str:
        """
        Format file list for display

        Args:
            files: List of file dicts from get_modified_files()
            max_display: Maximum number of files to include in detail

        Returns:
            Formatted string of file paths
        """
        if not files:
            return ""

        if len(files) <= max_display:
            return ", ".join(f['rel_path'] for f in files)
        else:
            displayed = ", ".join(f['rel_path'] for f in files[:max_display])
            return f"{displayed}, ... and {len(files) - max_display} more"

    def get_file_list_string(self, files: List[Dict[str, any]]) -> str:
        """
        Get comma-separated string of file paths for database storage

        Args:
            files: List of file dicts from get_modified_files()

        Returns:
            Comma-separated string of relative paths
        """
        if not files:
            return ""
        return ", ".join(f['rel_path'] for f in files)

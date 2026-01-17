"""System monitoring for idle detection and notifications"""

import threading
import time
from datetime import datetime
from typing import Optional, Callable
import platform


class IdleMonitor:
    """Monitors for idle time and triggers notifications"""

    def __init__(self, check_interval_seconds: int = 60):
        """
        Initialize idle monitor

        Args:
            check_interval_seconds: How often to check idle time (default 60)
        """
        self.check_interval = check_interval_seconds
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.idle_callback: Optional[Callable] = None
        self._last_check = datetime.now()

    def start(self, idle_callback: Callable):
        """
        Start monitoring in background thread

        Args:
            idle_callback: Function to call when idle threshold reached
                          Should return True if handled, False otherwise
        """
        if self.running:
            return

        self.idle_callback = idle_callback
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)"""
        while self.running:
            try:
                # Check if callback should be triggered
                if self.idle_callback:
                    # Call the callback - it will check idle conditions
                    self.idle_callback()

                # Sleep for check interval
                time.sleep(self.check_interval)

            except Exception as e:
                # Silently continue on errors to keep monitoring
                print(f"Idle monitor error: {e}")
                time.sleep(self.check_interval)


class WindowsNotifier:
    """Handles Windows notifications and window manipulation"""

    def __init__(self):
        self.notifier = None
        self._init_notifier()

    def _init_notifier(self):
        """Initialize the notification system"""
        if platform.system() != 'Windows':
            return

        try:
            from winotify import Notification
            self.notifier = Notification
        except ImportError:
            # winotify not available, will skip notifications
            pass

    def show_notification(self, title: str, message: str, duration: int = 10):
        """
        Show Windows toast notification

        Args:
            title: Notification title
            message: Notification message
            duration: How long to show (seconds)
        """
        if not self.notifier:
            return False

        try:
            def _show_toast():
                try:
                    toast = self.notifier(
                        app_id="Pomodoro Task Tracker",
                        title=title,
                        msg=message,
                        duration="short" if duration <= 5 else "long"
                    )
                    toast.show()
                except Exception as e:
                    print(f"Notification error: {e}")

            # Show notification in a separate thread to avoid blocking
            thread = threading.Thread(target=_show_toast, daemon=True)
            thread.start()
            return True
        except Exception as e:
            print(f"Notification error: {e}")
            return False

    def flash_taskbar(self, count: int = 3):
        """
        Flash the taskbar icon to get attention

        Args:
            count: Number of times to flash
        """
        if platform.system() != 'Windows':
            return False

        try:
            import ctypes

            # Get console window handle
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if not hwnd:
                return False

            # FLASHWINFO structure
            class FLASHWINFO(ctypes.Structure):
                _fields_ = [
                    ('cbSize', ctypes.c_uint),
                    ('hwnd', ctypes.c_void_p),
                    ('dwFlags', ctypes.c_uint),
                    ('uCount', ctypes.c_uint),
                    ('dwTimeout', ctypes.c_uint)
                ]

            # Flash flags
            FLASHW_ALL = 0x00000003  # Flash both taskbar button and window
            FLASHW_TIMERNOFG = 0x0000000C  # Flash until window comes to foreground

            flash_info = FLASHWINFO()
            flash_info.cbSize = ctypes.sizeof(FLASHWINFO)
            flash_info.hwnd = hwnd
            flash_info.dwFlags = FLASHW_ALL | FLASHW_TIMERNOFG
            flash_info.uCount = count
            flash_info.dwTimeout = 0

            ctypes.windll.user32.FlashWindowEx(ctypes.byref(flash_info))
            return True

        except Exception as e:
            print(f"Taskbar flash error: {e}")
            return False

    def bring_to_front(self):
        """Bring the console window to the foreground"""
        if platform.system() != 'Windows':
            return False

        try:
            import ctypes

            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                # SW_RESTORE = 9
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                return True
        except Exception as e:
            print(f"Bring to front error: {e}")

        return False


# Global instances
idle_monitor = IdleMonitor()
notifier = WindowsNotifier()

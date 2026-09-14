"""Windows window manager for detecting, focusing, and mapping Roblox coordinates."""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


class WindowManager:
    """Finds target game windows (like Roblox) and handles coordinate translation."""

    def __init__(self, target_title: str = "Roblox"):
        self.target_title = target_title

    def find_target_window(self) -> Optional[int]:
        """Finds the HWND (window handle) matching the target game window title."""
        if not HAS_WIN32:
            logger.warning("pywin32 not available; cannot search for window handles.")
            return None

        found_hwnd: Optional[int] = None

        def enum_windows_callback(hwnd, extra):
            nonlocal found_hwnd
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.target_title.lower() in title.lower():
                    found_hwnd = hwnd
                    return False
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception:
            # EnumWindows raises exception when callback returns False (which we use to stop early)
            pass

        return found_hwnd

    def get_window_rect(self, hwnd: Optional[int] = None) -> Optional[Tuple[int, int, int, int]]:
        """Returns (left, top, width, height) of the target window."""
        if not HAS_WIN32:
            return None

        target_hwnd = hwnd or self.find_target_window()
        if not target_hwnd:
            return None

        try:
            left, top, right, bottom = win32gui.GetWindowRect(target_hwnd)
            width = right - left
            height = bottom - top
            return (left, top, width, height)
        except Exception as e:
            logger.error("Failed to get window rect: %s", e)
            return None

    def focus_window(self, hwnd: Optional[int] = None) -> bool:
        """Brings the game window to the foreground."""
        if not HAS_WIN32:
            return False

        target_hwnd = hwnd or self.find_target_window()
        if not target_hwnd:
            logger.warning("Target window '%s' not found for focus.", self.target_title)
            return False

        try:
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(target_hwnd)
            return True
        except Exception as e:
            logger.error("Failed to focus window: %s", e)
            return False

    def window_to_screen_coords(self, rel_x: float, rel_y: float) -> Optional[Tuple[int, int]]:
        """Converts normalized (0.0 - 1.0) or relative window offsets to absolute screen pixels."""
        rect = self.get_window_rect()
        if not rect:
            return None

        left, top, width, height = rect
        abs_x = int(left + (rel_x * width if rel_x <= 1.0 else rel_x))
        abs_y = int(top + (rel_y * height if rel_y <= 1.0 else rel_y))
        return (abs_x, abs_y)


# Default window manager instance
window_manager = WindowManager()

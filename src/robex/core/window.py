"""Windows window manager for detecting, focusing, and mapping Roblox coordinates."""

import time
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


@dataclass
class WindowInfo:
    """Describes a single top-level window discovered during enumeration."""
    hwnd: int
    title: str
    rect: Tuple[int, int, int, int]  # (left, top, width, height)
    is_visible: bool


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

    def _is_real_app_window(self, hwnd) -> bool:
        """Returns True for windows a user would recognize from Alt-Tab.

        EnumWindows returns hundreds of hidden helper/message-only/tray-icon
        windows created by background processes (tool windows, owned popups,
        zero-size windows). Without this filter, list_open_windows() dumps
        all of them into the target dropdown alongside the handful of windows
        someone would actually want to automate.
        """
        if not win32gui.IsWindowVisible(hwnd):
            return False
        if not win32gui.GetWindowText(hwnd).strip():
            return False

        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if ex_style & win32con.WS_EX_TOOLWINDOW:
            return False

        # Owned windows (dialogs/popups belonging to another window) are only
        # kept if they explicitly opt in as a real app window.
        if win32gui.GetWindow(hwnd, win32con.GW_OWNER) != 0 and not (ex_style & win32con.WS_EX_APPWINDOW):
            return False

        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        except Exception:
            return False
        if (right - left) <= 0 or (bottom - top) <= 0:
            return False

        return True

    def list_open_windows(self, filter_empty: bool = True) -> List[WindowInfo]:
        """Enumerates the real, user-facing top-level windows currently open on
        the desktop (the same set you'd see cycling through Alt-Tab).

        This supports targeting any Roblox/Windows app dynamically instead of a
        single hardcoded title -- callers can inspect the returned titles/rects
        to pick a target window interactively.

        Args:
            filter_empty: When True (default), skips blank-titled, tool, owned,
                invisible, and zero-size windows -- i.e. everything that isn't a
                real application window a user would recognize.
        """
        if not HAS_WIN32:
            logger.warning("pywin32 not available; cannot enumerate windows.")
            return []

        windows: List[WindowInfo] = []

        def enum_windows_callback(hwnd, extra):
            if filter_empty and not self._is_real_app_window(hwnd):
                return True

            title = win32gui.GetWindowText(hwnd)
            if filter_empty and not title.strip():
                return True

            try:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                rect = (left, top, right - left, bottom - top)
            except Exception:
                rect = (0, 0, 0, 0)

            windows.append(WindowInfo(
                hwnd=hwnd,
                title=title,
                rect=rect,
                is_visible=win32gui.IsWindowVisible(hwnd),
            ))
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception as e:
            logger.error("Failed to enumerate windows: %s", e)

        return windows

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
        """Brings the game window to the foreground.

        Windows silently denies SetForegroundWindow calls made by a background
        process, so this attaches our thread's input queue to the target
        window's owning thread first (the standard AttachThreadInput trick) to
        make the foreground switch reliable, then falls back to
        BringWindowToTop / ShowWindow(SW_RESTORE) for minimized or stubborn
        windows.
        """
        if not HAS_WIN32:
            return False

        target_hwnd = hwnd or self.find_target_window()
        if not target_hwnd:
            logger.warning("Target window '%s' not found for focus.", self.target_title)
            return False

        try:
            if win32gui.IsIconic(target_hwnd):
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)

            current_thread_id = win32api.GetCurrentThreadId()
            target_thread_id, _ = win32process.GetWindowThreadProcessId(target_hwnd)

            attached = False
            if target_thread_id and target_thread_id != current_thread_id:
                try:
                    win32process.AttachThreadInput(current_thread_id, target_thread_id, True)
                    attached = True
                except Exception as e:
                    logger.debug("AttachThreadInput failed, continuing without it: %s", e)

            try:
                win32gui.BringWindowToTop(target_hwnd)
                win32gui.SetForegroundWindow(target_hwnd)
            finally:
                if attached:
                    try:
                        win32process.AttachThreadInput(current_thread_id, target_thread_id, False)
                    except Exception as e:
                        logger.debug("Failed to detach thread input: %s", e)

            # Final fallback restore in case foreground activation was silently
            # denied (e.g. target running under a different session/elevation).
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            return True
        except Exception as e:
            logger.error("Failed to focus window: %s", e)
            return False

    def is_target_focused(self) -> bool:
        """Returns True if the target window currently holds OS input focus."""
        if not HAS_WIN32:
            return False

        target_hwnd = self.find_target_window()
        if not target_hwnd:
            return False

        try:
            return win32gui.GetForegroundWindow() == target_hwnd
        except Exception as e:
            logger.error("Failed to check window focus: %s", e)
            return False

    def ensure_target_focused(self, timeout_sec: float = 1.0) -> bool:
        """Verifies the target window has focus, (re)focusing it if necessary.

        Used as a pre-execution guard so mouse/keyboard events dispatched by
        the macro runner land on the intended game/app rather than whatever
        window the user last clicked on.
        """
        if self.is_target_focused():
            return True

        if not self.focus_window():
            return False

        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            if self.is_target_focused():
                return True
            time.sleep(0.05)

        return self.is_target_focused()

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

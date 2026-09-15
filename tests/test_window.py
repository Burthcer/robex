"""Unit tests for the window manager: enumeration, focus validation, and runner integration.

Win32 APIs are mocked throughout so the suite runs deterministically in CI and on
non-Windows/mock environments (patching HAS_WIN32) without needing a real window.
"""

import time
from unittest.mock import patch

from robex.core.window import WindowManager, WindowInfo
from robex.engine.runner import MacroRunner
from robex.engine.actions import Action


class MockAction(Action):
    executed: bool = False
    action_type: str = "mock"

    def execute(self) -> None:
        self.executed = True


# --- Window enumeration -----------------------------------------------------

def test_list_open_windows_returns_window_info():
    manager = WindowManager(target_title="Roblox")

    def fake_enum_windows(callback, extra):
        callback(111, None)
        callback(222, None)

    with patch("robex.core.window.win32gui") as mock_gui:
        mock_gui.EnumWindows.side_effect = fake_enum_windows
        mock_gui.GetWindowText.side_effect = lambda hwnd: {111: "Roblox", 222: "Notepad"}[hwnd]
        mock_gui.GetWindowRect.side_effect = lambda hwnd: {
            111: (0, 0, 800, 600),
            222: (10, 10, 210, 110),
        }[hwnd]
        mock_gui.IsWindowVisible.return_value = True
        mock_gui.GetWindowLong.return_value = 0  # no WS_EX_TOOLWINDOW/APPWINDOW flags
        mock_gui.GetWindow.return_value = 0  # no owner -> a real top-level window

        windows = manager.list_open_windows()

    assert windows == [
        WindowInfo(hwnd=111, title="Roblox", rect=(0, 0, 800, 600), is_visible=True),
        WindowInfo(hwnd=222, title="Notepad", rect=(10, 10, 200, 100), is_visible=True),
    ]


def test_list_open_windows_filters_empty_titles_by_default():
    manager = WindowManager()

    def fake_enum_windows(callback, extra):
        callback(1, None)
        callback(2, None)

    with patch("robex.core.window.win32gui") as mock_gui:
        mock_gui.EnumWindows.side_effect = fake_enum_windows
        mock_gui.GetWindowText.side_effect = lambda hwnd: {1: "", 2: "Roblox"}[hwnd]
        mock_gui.GetWindowRect.return_value = (0, 0, 100, 100)
        mock_gui.IsWindowVisible.return_value = True
        mock_gui.GetWindowLong.return_value = 0
        mock_gui.GetWindow.return_value = 0

        windows = manager.list_open_windows(filter_empty=True)

    assert len(windows) == 1
    assert windows[0].title == "Roblox"


def test_list_open_windows_without_win32_returns_empty():
    manager = WindowManager()
    with patch("robex.core.window.HAS_WIN32", False):
        assert manager.list_open_windows() == []


def test_list_open_windows_excludes_tool_windows_and_owned_popups():
    """Regression test: EnumWindows returns hundreds of hidden helper/tray/tool
    windows -- only real Alt-Tab-style app windows should reach the dropdown."""
    manager = WindowManager()

    # hwnd 1: a real app window. hwnd 2: a tool window (e.g. a tray helper).
    # hwnd 3: a popup owned by another window, without WS_EX_APPWINDOW.
    def fake_enum_windows(callback, extra):
        for hwnd in (1, 2, 3):
            callback(hwnd, None)

    with patch("robex.core.window.win32gui") as mock_gui, \
         patch("robex.core.window.win32con") as mock_con:
        mock_con.GWL_EXSTYLE = -20
        mock_con.WS_EX_TOOLWINDOW = 0x80
        mock_con.WS_EX_APPWINDOW = 0x40000
        mock_con.GW_OWNER = 4

        mock_gui.EnumWindows.side_effect = fake_enum_windows
        mock_gui.GetWindowText.side_effect = lambda hwnd: {1: "Roblox", 2: "Tray Helper", 3: "Popup"}[hwnd]
        mock_gui.GetWindowRect.return_value = (0, 0, 100, 100)
        mock_gui.IsWindowVisible.return_value = True
        mock_gui.GetWindowLong.side_effect = lambda hwnd, flag: {
            1: 0,
            2: mock_con.WS_EX_TOOLWINDOW,
            3: 0,
        }[hwnd]
        mock_gui.GetWindow.side_effect = lambda hwnd, flag: {1: 0, 2: 0, 3: 999}[hwnd]

        windows = manager.list_open_windows()

    assert [w.title for w in windows] == ["Roblox"]


def test_list_open_windows_excludes_zero_size_windows():
    manager = WindowManager()

    def fake_enum_windows(callback, extra):
        callback(1, None)

    with patch("robex.core.window.win32gui") as mock_gui:
        mock_gui.EnumWindows.side_effect = fake_enum_windows
        mock_gui.GetWindowText.return_value = "Hidden Message Window"
        mock_gui.GetWindowRect.return_value = (0, 0, 0, 0)  # zero width/height
        mock_gui.IsWindowVisible.return_value = True
        mock_gui.GetWindowLong.return_value = 0
        mock_gui.GetWindow.return_value = 0

        windows = manager.list_open_windows()

    assert windows == []


# --- Coordinate mapping (existing behavior, still covered) -----------------

def test_window_to_screen_coords_normalized_offset():
    manager = WindowManager(target_title="Roblox")
    with patch.object(manager, "get_window_rect", return_value=(100, 50, 800, 600)):
        assert manager.window_to_screen_coords(0.5, 0.5) == (500, 350)


# --- Focus validation --------------------------------------------------------

def test_is_target_focused_true_when_hwnds_match():
    manager = WindowManager(target_title="Roblox")
    with patch.object(manager, "find_target_window", return_value=555), \
         patch("robex.core.window.win32gui") as mock_gui:
        mock_gui.GetForegroundWindow.return_value = 555
        assert manager.is_target_focused() is True


def test_is_target_focused_false_when_hwnds_differ():
    manager = WindowManager(target_title="Roblox")
    with patch.object(manager, "find_target_window", return_value=555), \
         patch("robex.core.window.win32gui") as mock_gui:
        mock_gui.GetForegroundWindow.return_value = 999
        assert manager.is_target_focused() is False


def test_is_target_focused_false_when_no_target_window():
    manager = WindowManager(target_title="Roblox")
    with patch.object(manager, "find_target_window", return_value=None):
        assert manager.is_target_focused() is False


def test_ensure_target_focused_short_circuits_when_already_focused():
    manager = WindowManager(target_title="Roblox")
    with patch.object(manager, "is_target_focused", return_value=True), \
         patch.object(manager, "focus_window") as mock_focus:
        assert manager.ensure_target_focused() is True
        mock_focus.assert_not_called()


def test_ensure_target_focused_refocuses_and_succeeds():
    manager = WindowManager(target_title="Roblox")
    with patch.object(manager, "is_target_focused", side_effect=[False, True]), \
         patch.object(manager, "focus_window", return_value=True) as mock_focus:
        assert manager.ensure_target_focused(timeout_sec=0.2) is True
        mock_focus.assert_called_once()


def test_ensure_target_focused_gives_up_when_window_not_found():
    manager = WindowManager(target_title="Roblox")
    with patch.object(manager, "is_target_focused", return_value=False), \
         patch.object(manager, "focus_window", return_value=False):
        assert manager.ensure_target_focused(timeout_sec=0.1) is False


def test_ensure_target_focused_without_win32_returns_false():
    manager = WindowManager()
    with patch("robex.core.window.HAS_WIN32", False):
        assert manager.ensure_target_focused(timeout_sec=0.05) is False


# --- Robust foreground restoration ------------------------------------------

def test_focus_window_attaches_and_detaches_thread_input():
    manager = WindowManager(target_title="Roblox")
    with patch.object(manager, "find_target_window", return_value=42), \
         patch("robex.core.window.win32gui") as mock_gui, \
         patch("robex.core.window.win32process") as mock_process, \
         patch("robex.core.window.win32api") as mock_api:
        mock_gui.IsIconic.return_value = False
        mock_api.GetCurrentThreadId.return_value = 1
        mock_process.GetWindowThreadProcessId.return_value = (2, 9999)

        assert manager.focus_window() is True

        mock_process.AttachThreadInput.assert_any_call(1, 2, True)
        mock_process.AttachThreadInput.assert_any_call(1, 2, False)
        mock_gui.SetForegroundWindow.assert_called_once_with(42)


def test_focus_window_restores_minimized_window():
    manager = WindowManager(target_title="Roblox")
    with patch.object(manager, "find_target_window", return_value=42), \
         patch("robex.core.window.win32gui") as mock_gui, \
         patch("robex.core.window.win32con") as mock_con, \
         patch("robex.core.window.win32process") as mock_process, \
         patch("robex.core.window.win32api") as mock_api:
        mock_gui.IsIconic.return_value = True
        mock_con.SW_RESTORE = "SW_RESTORE"
        mock_api.GetCurrentThreadId.return_value = 1
        mock_process.GetWindowThreadProcessId.return_value = (1, 9999)  # same thread, no attach

        assert manager.focus_window() is True

        mock_gui.ShowWindow.assert_any_call(42, "SW_RESTORE")
        mock_process.AttachThreadInput.assert_not_called()


def test_focus_window_without_target_returns_false():
    manager = WindowManager(target_title="Roblox")
    with patch.object(manager, "find_target_window", return_value=None):
        assert manager.focus_window() is False


# --- Runner integration ------------------------------------------------------

def test_runner_focus_guard_disabled_by_default():
    runner = MacroRunner()
    action = MockAction()
    runner.load_actions([action], repeat_count=1)

    with patch("robex.engine.runner.window_manager") as mock_wm:
        runner.start()
        time.sleep(0.15)
        mock_wm.ensure_target_focused.assert_not_called()

    assert action.executed


def test_runner_focus_guard_calls_ensure_target_focused_when_enabled():
    runner = MacroRunner()
    runner.set_require_focus(True)
    action = MockAction()
    runner.load_actions([action], repeat_count=1)

    with patch("robex.engine.runner.window_manager") as mock_wm:
        mock_wm.ensure_target_focused.return_value = True
        runner.start()
        time.sleep(0.15)
        mock_wm.ensure_target_focused.assert_called()

    assert action.executed


def test_runner_focus_guard_failure_does_not_abort_macro():
    runner = MacroRunner()
    runner.set_require_focus(True)
    action = MockAction()
    runner.load_actions([action], repeat_count=1)

    with patch("robex.engine.runner.window_manager") as mock_wm:
        mock_wm.ensure_target_focused.return_value = False
        runner.start()
        time.sleep(0.15)

    assert action.executed

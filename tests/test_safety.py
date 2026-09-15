"""Unit tests for safety killswitch controller."""

from unittest.mock import patch
import pytest
from robex.core.safety import SafetyController, EmergencyStopTriggered

# A cursor position safely away from any screen corner, for tests that aren't
# specifically exercising the corner fail-safe (it's on by default).
_CENTER = ((960, 540), (1920, 1080))


def test_safety_initial_state():
    safety = SafetyController(killswitch_key="f12", corner_failsafe=False)
    assert not safety.is_halted
    # Should not raise
    safety.assert_safe()


def test_safety_trigger_killswitch():
    safety = SafetyController(corner_failsafe=False)
    callback_executed = False

    def abort_hook():
        nonlocal callback_executed
        callback_executed = True

    safety.register_abort_callback(abort_hook)
    safety.trigger_killswitch("Test trigger")

    assert safety.is_halted
    assert callback_executed

    with pytest.raises(EmergencyStopTriggered):
        safety.assert_safe()


def test_safety_reset():
    safety = SafetyController(corner_failsafe=False)
    safety.trigger_killswitch()
    assert safety.is_halted

    safety.reset()
    assert not safety.is_halted
    safety.assert_safe()


# --- Corner fail-safe -------------------------------------------------------
# This replaces pydirectinput/pyautogui's own bundled corner fail-safe (which
# is disabled in input_driver.py): their check runs against the cursor's
# *starting* position before every single move, so if the cursor is merely
# resting in a corner when a macro starts, it permanently refuses to move the
# mouse at all -- see the regression tests below and in test_input_driver.py.

def test_cursor_in_corner_true_for_all_four_corners():
    safety = SafetyController()
    corners = [(0, 0), (1919, 0), (0, 1079), (1919, 1079)]
    for x, y in corners:
        with patch.object(safety, "_get_cursor_and_screen", return_value=((x, y), (1920, 1080))):
            assert safety._cursor_in_corner() is True, f"expected corner at {(x, y)} to be detected"


def test_cursor_in_corner_false_for_center():
    safety = SafetyController()
    with patch.object(safety, "_get_cursor_and_screen", return_value=_CENTER):
        assert safety._cursor_in_corner() is False


def test_cursor_in_corner_false_for_edge_midpoint():
    """Being at x=0 (left edge) but vertically centered is NOT a corner."""
    safety = SafetyController()
    with patch.object(safety, "_get_cursor_and_screen", return_value=((0, 540), (1920, 1080))):
        assert safety._cursor_in_corner() is False


def test_cursor_in_corner_respects_margin():
    safety = SafetyController()
    with patch.object(safety, "_get_cursor_and_screen", return_value=((3, 3), (1920, 1080))):
        assert safety._cursor_in_corner() is True  # within the 5px margin
    with patch.object(safety, "_get_cursor_and_screen", return_value=((20, 20), (1920, 1080))):
        assert safety._cursor_in_corner() is False  # outside the margin


def test_cursor_in_corner_false_when_position_unavailable():
    safety = SafetyController()
    with patch.object(safety, "_get_cursor_and_screen", return_value=None):
        assert safety._cursor_in_corner() is False


def test_assert_safe_triggers_killswitch_when_cursor_in_corner():
    safety = SafetyController()
    with patch.object(safety, "_get_cursor_and_screen", return_value=((0, 0), (1920, 1080))):
        with pytest.raises(EmergencyStopTriggered):
            safety.assert_safe()
    assert safety.is_halted


def test_assert_safe_does_not_trigger_when_cursor_not_in_corner():
    safety = SafetyController()
    with patch.object(safety, "_get_cursor_and_screen", return_value=_CENTER):
        safety.assert_safe()  # should not raise
    assert not safety.is_halted


def test_assert_safe_ignores_corner_when_corner_failsafe_disabled():
    safety = SafetyController(corner_failsafe=False)
    with patch.object(safety, "_get_cursor_and_screen", return_value=((0, 0), (1920, 1080))):
        safety.assert_safe()  # should not raise -- feature is opted out
    assert not safety.is_halted


def test_assert_safe_runs_abort_callbacks_on_corner_trigger():
    safety = SafetyController()
    released = []
    safety.register_abort_callback(lambda: released.append(True))

    with patch.object(safety, "_get_cursor_and_screen", return_value=((0, 0), (1920, 1080))):
        with pytest.raises(EmergencyStopTriggered):
            safety.assert_safe()

    assert released == [True]


def test_assert_safe_corner_trigger_is_recoverable_via_reset():
    """The corner fail-safe must abort cleanly, not deadlock -- once reset (and
    the cursor moved away), automation can resume normally."""
    safety = SafetyController()

    with patch.object(safety, "_get_cursor_and_screen", return_value=((0, 0), (1920, 1080))):
        with pytest.raises(EmergencyStopTriggered):
            safety.assert_safe()
    assert safety.is_halted

    safety.reset()
    with patch.object(safety, "_get_cursor_and_screen", return_value=_CENTER):
        safety.assert_safe()  # cursor moved away -- no longer raises
    assert not safety.is_halted


def test_assert_safe_does_not_retrigger_killswitch_once_already_halted():
    """trigger_killswitch() is already idempotent; corner-checking every
    assert_safe() call must not re-run abort callbacks repeatedly."""
    safety = SafetyController()
    call_count = 0

    def counting_callback():
        nonlocal call_count
        call_count += 1

    safety.register_abort_callback(counting_callback)

    with patch.object(safety, "_get_cursor_and_screen", return_value=((0, 0), (1920, 1080))):
        for _ in range(5):
            with pytest.raises(EmergencyStopTriggered):
                safety.assert_safe()

    assert call_count == 1


def test_get_cursor_and_screen_returns_none_without_ctypes_windll():
    safety = SafetyController()
    with patch("robex.core.safety.HAS_CTYPES_WIN", False):
        assert safety._get_cursor_and_screen() is None

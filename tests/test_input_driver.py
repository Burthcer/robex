"""Unit tests for the DirectInput/pyautogui input driver.

pydirectinput/pyautogui calls are mocked throughout so these tests never move
the real mouse cursor or send real key events during an automated test run.
"""

from unittest.mock import patch
import robex.core.input_driver as input_driver_module
from robex.core.input_driver import InputDriver


def test_failsafe_disabled_on_both_libraries():
    """Regression test for the corner-fail-safe deadlock: pydirectinput's (and
    pyautogui's) own bundled corner fail-safe checks the cursor's *starting*
    position before every single move. If the cursor is merely resting in a
    corner when a macro starts, it permanently refuses to move the mouse at
    all -- with no way to move it away, since even the recovery move is
    itself blocked. Robex's own corner fail-safe (SafetyController, checked
    via assert_safe()) replaces it, so both libraries' FAILSAFE must stay off.
    """
    if input_driver_module.HAS_DIRECTINPUT:
        assert input_driver_module.pydirectinput.FAILSAFE is False
    if input_driver_module.HAS_PYAUTOGUI:
        assert input_driver_module.pyautogui.FAILSAFE is False


def test_click_moves_then_presses_and_releases():
    driver = InputDriver(human_jitter=False)
    with patch.object(input_driver_module, "pydirectinput") as mock_pdi:
        driver.click(x=100, y=200, button="left")

        mock_pdi.moveTo.assert_called_once_with(100, 200, duration=0.0)
        mock_pdi.mouseDown.assert_called_once_with(button="left")
        mock_pdi.mouseUp.assert_called_once_with(button="left")


def test_click_without_coords_does_not_move():
    driver = InputDriver(human_jitter=False)
    with patch.object(input_driver_module, "pydirectinput") as mock_pdi:
        driver.click()
        mock_pdi.moveTo.assert_not_called()
        mock_pdi.mouseDown.assert_called_once()


def test_mouse_down_tracks_held_buttons():
    driver = InputDriver(human_jitter=False)
    with patch.object(input_driver_module, "pydirectinput"):
        driver.mouse_down("left")
        assert "left" in driver._held_mouse_buttons
        driver.mouse_up("left")
        assert "left" not in driver._held_mouse_buttons


def test_key_down_tracks_held_keys():
    driver = InputDriver(human_jitter=False)
    with patch.object(input_driver_module, "pydirectinput"):
        driver.key_down("w")
        assert "w" in driver._held_keys
        driver.key_up("w")
        assert "w" not in driver._held_keys


def test_release_all_releases_every_held_key_and_button():
    driver = InputDriver(human_jitter=False)
    with patch.object(input_driver_module, "pydirectinput") as mock_pdi:
        driver.key_down("w")
        driver.key_down("shift")
        driver.mouse_down("left")

        driver.release_all()

        assert driver._held_keys == set()
        assert driver._held_mouse_buttons == set()
        assert mock_pdi.keyUp.call_count == 2
        mock_pdi.mouseUp.assert_called_once_with(button="left")


def test_release_all_registered_as_safety_abort_callback():
    """release_all must fire automatically when the killswitch trips, so a
    corner-fail-safe or F12 abort mid-hold doesn't leave keys stuck down."""
    from robex.core.safety import SafetyController

    isolated_safety = SafetyController(corner_failsafe=False)
    with patch.object(input_driver_module, "global_safety", isolated_safety):
        driver = InputDriver(human_jitter=False)
        with patch.object(input_driver_module, "pydirectinput") as mock_pdi:
            driver.key_down("w")
            isolated_safety.trigger_killswitch("test abort")

            assert driver._held_keys == set()
            mock_pdi.keyUp.assert_called_with("w")

"""Unit tests for safety killswitch controller."""

import pytest
from robex.core.safety import SafetyController, EmergencyStopTriggered


def test_safety_initial_state():
    safety = SafetyController(killswitch_key="f12")
    assert not safety.is_halted
    # Should not raise
    safety.assert_safe()


def test_safety_trigger_killswitch():
    safety = SafetyController()
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
    safety = SafetyController()
    safety.trigger_killswitch()
    assert safety.is_halted

    safety.reset()
    assert not safety.is_halted
    safety.assert_safe()

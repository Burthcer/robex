"""Unit tests for action serialization and primitives."""

import pytest
from robex.engine.actions import (
    ClickAction,
    VisionClickAction,
    KeyPressAction,
    KeyHoldAction,
    StuntAction,
    action_from_dict
)


def test_click_action_serialization():
    act = ClickAction(x=100, y=200, button="left", clicks=2)
    d = act.to_dict()
    assert d["x"] == 100
    assert d["y"] == 200
    assert d["button"] == "left"
    assert d["clicks"] == 2

    reconstructed = action_from_dict(d)
    assert isinstance(reconstructed, ClickAction)
    assert reconstructed.x == 100
    assert reconstructed.y == 200


def test_vision_click_action_serialization():
    act = VisionClickAction(target_color="green", timeout_sec=2.5)
    d = act.to_dict()
    assert d["target_color"] == "green"
    assert d["timeout_sec"] == 2.5

    reconstructed = action_from_dict(d)
    assert isinstance(reconstructed, VisionClickAction)
    assert reconstructed.target_color == "green"


def test_key_actions_serialization():
    press = KeyPressAction(key="space", duration=0.08)
    d_press = press.to_dict()
    rec_press = action_from_dict(d_press)
    assert isinstance(rec_press, KeyPressAction)
    assert rec_press.key == "space"

    hold = KeyHoldAction(key="w", duration=3.0)
    d_hold = hold.to_dict()
    rec_hold = action_from_dict(d_hold)
    assert isinstance(rec_hold, KeyHoldAction)
    assert rec_hold.key == "w"
    assert rec_hold.duration == 3.0


def test_stunt_action_serialization():
    stunt = StuntAction(stunt_name="double_jump")
    d_stunt = stunt.to_dict()
    rec_stunt = action_from_dict(d_stunt)
    assert isinstance(rec_stunt, StuntAction)
    assert rec_stunt.stunt_name == "double_jump"


def test_unknown_action_type_raises():
    with pytest.raises(ValueError):
        action_from_dict({"type": "non_existent_action_type"})

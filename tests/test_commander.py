"""Unit tests for the natural language command parser."""

from robex.ai.commander import CommandParser
from robex.engine.actions import (
    VisionClickAction,
    ClickAction,
    KeyPressAction,
    KeyHoldAction,
    StuntAction,
    WaitAction
)


def test_parse_vision_click():
    parser = CommandParser()
    actions = parser.parse_instruction("click the green button")
    assert len(actions) == 1
    assert isinstance(actions[0], VisionClickAction)
    assert actions[0].target_color == "green"


def test_parse_coords_click():
    parser = CommandParser()
    actions = parser.parse_instruction("click at 400, 300")
    assert len(actions) == 1
    assert isinstance(actions[0], ClickAction)
    assert actions[0].x == 400
    assert actions[0].y == 300


def test_parse_compound_sentence():
    parser = CommandParser()
    cmd = "click green button, then wait 1.5s, then jump, then hold w for 2s"
    actions = parser.parse_instruction(cmd)

    assert len(actions) == 4
    assert isinstance(actions[0], VisionClickAction)
    assert isinstance(actions[1], WaitAction)
    assert actions[1].duration == 1.5
    assert isinstance(actions[2], KeyPressAction)
    assert actions[2].key == "space"
    assert isinstance(actions[3], KeyHoldAction)
    assert actions[3].key == "w"
    assert actions[3].duration == 2.0


def test_parse_stunts():
    parser = CommandParser()
    actions = parser.parse_instruction("double jump; turn 180")
    assert len(actions) == 2
    assert isinstance(actions[0], StuntAction)
    assert actions[0].stunt_name == "double_jump"
    assert isinstance(actions[1], StuntAction)
    assert actions[1].stunt_name == "turn_180"


def test_parse_empty_or_whitespace():
    parser = CommandParser()
    assert parser.parse_instruction("") == []
    assert parser.parse_instruction("   \n\t  ") == []


def test_parse_typo_and_filler_tolerant():
    parser = CommandParser()
    actions = parser.parse_instruction("please clck the gern botton")
    assert len(actions) == 1
    assert isinstance(actions[0], VisionClickAction)
    assert actions[0].target_color == "green"


def test_parse_multiline_dictated_paragraph():
    parser = CommandParser()
    text = "clck gern botton\num wait 1.5 seconds\njump"
    actions = parser.parse_instruction(text)
    assert len(actions) == 3
    assert isinstance(actions[0], VisionClickAction)
    assert actions[0].target_color == "green"
    assert isinstance(actions[1], WaitAction)
    assert actions[1].duration == 1.5
    assert isinstance(actions[2], KeyPressAction)
    assert actions[2].key == "space"


def test_parse_non_color_button_description_routes_to_semantic_query():
    parser = CommandParser()
    actions = parser.parse_instruction("click the auto sell button")
    assert len(actions) == 1
    assert isinstance(actions[0], VisionClickAction)
    assert actions[0].query == "auto sell"
    assert actions[0].target_color == "green"  # unused when query is set


def test_parse_free_form_sentence_with_embedded_delay_produces_click_and_wait():
    parser = CommandParser()
    text = "I want you to click the auto sell button again with an essentially delay of about 1 second."
    actions = parser.parse_instruction(text)

    assert len(actions) == 2
    assert isinstance(actions[0], VisionClickAction)
    assert actions[0].query == "auto sell"
    assert isinstance(actions[1], WaitAction)
    assert actions[1].duration == 1.0


def test_parse_every_n_seconds_phrase_produces_wait():
    parser = CommandParser()
    actions = parser.parse_instruction("click the shop icon every 2 seconds")
    assert len(actions) == 2
    assert isinstance(actions[0], VisionClickAction)
    assert actions[0].query == "shop"
    assert isinstance(actions[1], WaitAction)
    assert actions[1].duration == 2.0

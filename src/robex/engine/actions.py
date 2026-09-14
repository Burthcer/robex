"""Atomic macro action primitives and serializable action descriptors."""

from dataclasses import dataclass, asdict
from typing import Dict, Any
import time
import logging

from robex.core.safety import global_safety
from robex.core.input_driver import driver
from robex.vision.screen import screen_grabber
from robex.vision.detector import detector

logger = logging.getLogger(__name__)


@dataclass
class Action:
    """Base class for all executable macro actions."""
    action_type: str = "base"

    def execute(self) -> None:
        """Executes the action. Subclasses must implement."""
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClickAction(Action):
    """Clicks specific screen coordinates."""
    x: int = 0
    y: int = 0
    button: str = "left"
    clicks: int = 1
    action_type: str = "click"

    def execute(self) -> None:
        global_safety.assert_safe()
        logger.debug("Executing click at (%d, %d)", self.x, self.y)
        driver.click(x=self.x, y=self.y, button=self.button, clicks=self.clicks)


@dataclass
class VisionClickAction(Action):
    """Finds a target on screen (e.g. green button) and clicks its center."""
    target_color: str = "green"
    button: str = "left"
    timeout_sec: float = 3.0
    action_type: str = "vision_click"

    def execute(self) -> None:
        global_safety.assert_safe()
        logger.debug("Executing vision click for target: %s", self.target_color)

        start_time = time.time()
        while time.time() - start_time < self.timeout_sec:
            global_safety.assert_safe()
            frame = screen_grabber.grab_screen()
            if frame is not None:
                matches = detector.find_buttons_by_color(frame, self.target_color)
                if matches:
                    best = matches[0]
                    logger.info("Found %s button at (%d, %d) with confidence %.2f",
                                self.target_color, best.x, best.y, best.confidence)
                    driver.click(x=best.x, y=best.y, button=self.button)
                    return
            time.sleep(0.1)

        logger.warning("Vision click timed out: %s button not found on screen.", self.target_color)


@dataclass
class KeyPressAction(Action):
    """Taps a keyboard key (e.g., jump, interact)."""
    key: str = "space"
    duration: float = 0.05
    action_type: str = "key_press"

    def execute(self) -> None:
        global_safety.assert_safe()
        logger.debug("Tapping key '%s' for %.2fs", self.key, self.duration)
        driver.key_press(self.key, duration=self.duration)


@dataclass
class KeyHoldAction(Action):
    """Holds a key down for continuous movement (e.g. holding W to walk forward)."""
    key: str = "w"
    duration: float = 1.0
    action_type: str = "key_hold"

    def execute(self) -> None:
        global_safety.assert_safe()
        logger.debug("Holding key '%s' for %.2fs", self.key, self.duration)
        driver.hold_key(self.key, duration=self.duration)


@dataclass
class StuntAction(Action):
    """Executes a composite movement stunt (e.g., jump_forward, double_jump, turn_180)."""
    stunt_name: str = "jump_forward"
    action_type: str = "stunt"

    def execute(self) -> None:
        global_safety.assert_safe()
        logger.info("Executing stunt: %s", self.stunt_name)
        driver.perform_stunt(self.stunt_name)


@dataclass
class WaitAction(Action):
    """Pauses execution for a set duration, checking killswitch every 50ms."""
    duration: float = 1.0
    action_type: str = "wait"

    def execute(self) -> None:
        start_time = time.time()
        while time.time() - start_time < self.duration:
            global_safety.assert_safe()
            time.sleep(min(0.05, self.duration - (time.time() - start_time)))


def action_from_dict(data: Dict[str, Any]) -> Action:
    """Deserializes an action dictionary into its concrete Action dataclass."""
    atype = data.get("type", data.get("action_type", ""))
    if atype == "click":
        return ClickAction(
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            button=data.get("button", "left"),
            clicks=int(data.get("clicks", 1))
        )
    elif atype == "vision_click":
        return VisionClickAction(
            target_color=data.get("target_color", data.get("color", "green")),
            button=data.get("button", "left"),
            timeout_sec=float(data.get("timeout_sec", 3.0))
        )
    elif atype == "key_press":
        return KeyPressAction(
            key=data.get("key", "space"),
            duration=float(data.get("duration", 0.05))
        )
    elif atype == "key_hold":
        return KeyHoldAction(
            key=data.get("key", "w"),
            duration=float(data.get("duration", 1.0))
        )
    elif atype == "stunt":
        return StuntAction(
            stunt_name=data.get("stunt_name", data.get("stunt", "jump_forward"))
        )
    elif atype == "wait":
        return WaitAction(
            duration=float(data.get("duration", 1.0))
        )
    else:
        raise ValueError(f"Unknown action type: {atype}")

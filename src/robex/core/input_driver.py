"""DirectInput & SendInput hardware simulator for Roblox and desktop games.

Provides reliable game movement (WASD, jumps, camera drag), button clicking,
and auto-release safety hooks to prevent keys from getting stuck down.
"""

import time
import random
import logging
from typing import Set, Tuple, Optional
from robex.core.safety import global_safety

logger = logging.getLogger(__name__)

# Try importing pydirectinput for DirectX / DirectInput game compatibility
try:
    import pydirectinput
    # Configure pydirectinput defaults
    pydirectinput.PAUSE = 0.01
    pydirectinput.FAILSAFE = True
    HAS_DIRECTINPUT = True
except ImportError:
    pydirectinput = None
    HAS_DIRECTINPUT = False

# Fallback to pyautogui
try:
    import pyautogui
    pyautogui.PAUSE = 0.01
    pyautogui.FAILSAFE = True
    HAS_PYAUTOGUI = True
except ImportError:
    pyautogui = None
    HAS_PYAUTOGUI = False


class InputDriver:
    """Manages synthetic mouse and keyboard inputs with game compatibility and safety."""

    def __init__(self, human_jitter: bool = True, default_click_delay_ms: int = 50):
        self.human_jitter = human_jitter
        self.default_click_delay = default_click_delay_ms / 1000.0
        self._held_keys: Set[str] = set()
        self._held_mouse_buttons: Set[str] = set()

        # Register auto-release callback with global safety killswitch
        global_safety.register_abort_callback(self.release_all)

    # -------------------------------------------------------------------------
    # Mouse Operations
    # -------------------------------------------------------------------------

    def get_mouse_position(self) -> Tuple[int, int]:
        """Returns the current cursor position (x, y)."""
        if HAS_PYAUTOGUI:
            return pyautogui.position()
        elif HAS_DIRECTINPUT:
            return pydirectinput.position()
        return (0, 0)

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        """Moves cursor to target screen coordinates."""
        global_safety.assert_safe()

        if self.human_jitter and duration > 0:
            # Add micro-variation to movement
            x += random.randint(-1, 1)
            y += random.randint(-1, 1)

        if HAS_DIRECTINPUT:
            pydirectinput.moveTo(int(x), int(y), duration=duration)
        elif HAS_PYAUTOGUI:
            pyautogui.moveTo(int(x), int(y), duration=duration)

    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1) -> None:
        """Clicks at coordinates (or current position) with natural press/release timing."""
        global_safety.assert_safe()

        if x is not None and y is not None:
            self.move_to(x, y)

        for _ in range(clicks):
            global_safety.assert_safe()
            self.mouse_down(button)
            time.sleep(self.default_click_delay + (random.uniform(0.01, 0.03) if self.human_jitter else 0))
            self.mouse_up(button)
            if clicks > 1:
                time.sleep(0.05)

    def mouse_down(self, button: str = "left") -> None:
        """Presses down a mouse button without releasing it."""
        global_safety.assert_safe()
        self._held_mouse_buttons.add(button.lower())

        if HAS_DIRECTINPUT:
            pydirectinput.mouseDown(button=button)
        elif HAS_PYAUTOGUI:
            pyautogui.mouseDown(button=button)

    def mouse_up(self, button: str = "left") -> None:
        """Releases a previously pressed mouse button."""
        self._held_mouse_buttons.discard(button.lower())

        if HAS_DIRECTINPUT:
            pydirectinput.mouseUp(button=button)
        elif HAS_PYAUTOGUI:
            pyautogui.mouseUp(button=button)

    def rotate_camera(self, delta_x: int, delta_y: int, duration: float = 0.3) -> None:
        """Simulates right-click camera drag for Roblox 3D navigation."""
        global_safety.assert_safe()
        cur_x, cur_y = self.get_mouse_position()

        self.mouse_down("right")
        try:
            steps = 10
            sleep_step = duration / steps
            for i in range(1, steps + 1):
                global_safety.assert_safe()
                step_x = cur_x + int(delta_x * (i / steps))
                step_y = cur_y + int(delta_y * (i / steps))
                self.move_to(step_x, step_y)
                time.sleep(sleep_step)
        finally:
            self.mouse_up("right")

    # -------------------------------------------------------------------------
    # Keyboard Operations
    # -------------------------------------------------------------------------

    def key_press(self, key: str, duration: float = 0.05) -> None:
        """Presses and releases a key (e.g. 'space' for jump, 'e' for interact)."""
        global_safety.assert_safe()
        key = key.lower()
        self.key_down(key)
        time.sleep(max(0.02, duration))
        self.key_up(key)

    def key_down(self, key: str) -> None:
        """Holds down a key (e.g. 'w' to walk forward)."""
        global_safety.assert_safe()
        key = key.lower()
        self._held_keys.add(key)

        if HAS_DIRECTINPUT:
            pydirectinput.keyDown(key)
        elif HAS_PYAUTOGUI:
            pyautogui.keyDown(key)

    def key_up(self, key: str) -> None:
        """Releases a held key."""
        key = key.lower()
        self._held_keys.discard(key)

        if HAS_DIRECTINPUT:
            pydirectinput.keyUp(key)
        elif HAS_PYAUTOGUI:
            pyautogui.keyUp(key)

    def hold_key(self, key: str, duration: float) -> None:
        """Holds a key for a specific duration (checks killswitch every 50ms)."""
        global_safety.assert_safe()
        key = key.lower()
        self.key_down(key)
        try:
            start_time = time.time()
            while (time.time() - start_time) < duration:
                global_safety.assert_safe()
                time.sleep(min(0.05, duration - (time.time() - start_time)))
        finally:
            self.key_up(key)

    def perform_stunt(self, stunt_type: str) -> None:
        """Executes predefined game maneuvers (e.g., jump-dash, double-jump, 180-turn)."""
        global_safety.assert_safe()
        stunt = stunt_type.lower()

        if stunt == "jump_forward":
            # Hold W and tap Space
            self.key_down("w")
            time.sleep(0.1)
            self.key_press("space", 0.08)
            time.sleep(0.4)
            self.key_up("w")

        elif stunt == "double_jump":
            self.key_press("space", 0.06)
            time.sleep(0.15)
            self.key_press("space", 0.06)

        elif stunt == "turn_180":
            # Drag camera 180 degrees horizontally
            self.rotate_camera(delta_x=300, delta_y=0, duration=0.2)

        else:
            logger.warning("Unknown stunt requested: %s", stunt_type)

    # -------------------------------------------------------------------------
    # Safety Release
    # -------------------------------------------------------------------------

    def release_all(self) -> None:
        """Safety callback: immediately releases all active keys and mouse buttons."""
        logger.info("Safety release: releasing all held keys (%s) and mouse buttons (%s)",
                    self._held_keys, self._held_mouse_buttons)

        # Release mouse buttons
        for btn in list(self._held_mouse_buttons):
            try:
                if HAS_DIRECTINPUT:
                    pydirectinput.mouseUp(button=btn)
                elif HAS_PYAUTOGUI:
                    pyautogui.mouseUp(button=btn)
            except Exception as e:
                logger.error("Failed to release mouse button %s: %s", btn, e)
        self._held_mouse_buttons.clear()

        # Release keys
        for k in list(self._held_keys):
            try:
                if HAS_DIRECTINPUT:
                    pydirectinput.keyUp(k)
                elif HAS_PYAUTOGUI:
                    pyautogui.keyUp(k)
            except Exception as e:
                logger.error("Failed to release key %s: %s", k, e)
        self._held_keys.clear()


# Default singleton driver
driver = InputDriver()

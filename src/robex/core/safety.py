"""Global safety controller and emergency killswitch for Robex.

Provides thread-safe abort signals, emergency hotkey listeners (e.g. F12),
and input-release guarantees to ensure automation never locks the user's desktop.
"""

import threading
import logging
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class EmergencyStopTriggered(Exception):
    """Exception raised when an automation task is halted by the emergency killswitch."""
    pass


class SafetyController:
    """Coordinates killswitch hotkeys, emergency stop flags, and abort callbacks."""

    def __init__(self, killswitch_key: str = "f12", corner_failsafe: bool = True):
        self.killswitch_key = killswitch_key.lower()
        self.corner_failsafe = corner_failsafe
        self._halt_event = threading.Event()
        self._callbacks: List[Callable[[], None]] = []
        self._listener: Optional[object] = None
        self._listener_lock = threading.Lock()

    @property
    def is_halted(self) -> bool:
        """Returns True if an emergency stop or stop signal has been issued."""
        return self._halt_event.is_set()

    def register_abort_callback(self, callback: Callable[[], None]) -> None:
        """Register a function to be executed immediately when killswitch fires."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_abort_callback(self, callback: Callable[[], None]) -> None:
        """Unregister an abort callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def trigger_killswitch(self, reason: str = "Emergency killswitch activated") -> None:
        """Immediately halts all automation and invokes abort callbacks."""
        if self._halt_event.is_set():
            return

        logger.warning("KILLSWITCH TRIGGERED: %s", reason)
        self._halt_event.set()

        # Execute callbacks (e.g., releasing stuck keys/mouse buttons)
        for cb in list(self._callbacks):
            try:
                cb()
            except Exception as e:
                logger.error("Error executing safety abort callback: %s", e)

    def reset(self) -> None:
        """Resets the halt flag so automation can be started again."""
        self._halt_event.clear()
        logger.info("Safety controller reset. Automation ready.")

    def assert_safe(self) -> None:
        """Raises EmergencyStopTriggered if the killswitch has been activated."""
        if self.is_halted:
            raise EmergencyStopTriggered("Action aborted: emergency killswitch is active.")

    def start_listener(self) -> None:
        """Starts listening in the background for the killswitch hotkey."""
        with self._listener_lock:
            if self._listener is not None:
                return

            try:
                from pynput import keyboard

                def on_press(key):
                    try:
                        # Check function keys (f1 - f12)
                        key_name = None
                        if hasattr(key, "name"):
                            key_name = key.name.lower()
                        elif hasattr(key, "char") and key.char:
                            key_name = key.char.lower()

                        if key_name == self.killswitch_key:
                            logger.critical(
                                "Killswitch hotkey [%s] pressed by user!", self.killswitch_key
                            )
                            self.trigger_killswitch(f"Hotkey {self.killswitch_key} pressed")
                    except Exception as e:
                        logger.error("Error in safety keyboard listener: %s", e)

                listener = keyboard.Listener(on_press=on_press)
                listener.daemon = True
                listener.start()
                self._listener = listener
                logger.info("Safety hotkey listener started for key [%s].", self.killswitch_key)
            except ImportError:
                logger.warning("pynput not installed; global hotkey listener is inactive.")

    def stop_listener(self) -> None:
        """Stops the background keyboard listener."""
        with self._listener_lock:
            if self._listener is not None:
                try:
                    self._listener.stop()
                except Exception as e:
                    logger.debug("Error stopping safety listener: %s", e)
                self._listener = None


# Global singleton instance for easy access across the entire app
global_safety = SafetyController()

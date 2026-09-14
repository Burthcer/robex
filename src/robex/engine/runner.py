"""Threaded macro execution runner with state management and killswitch integration."""

import threading
import time
import logging
from enum import Enum
from typing import List, Callable, Optional

from robex.core.safety import global_safety, EmergencyStopTriggered
from robex.core.window import window_manager
from robex.engine.actions import Action
from robex.engine.history import history_recorder

logger = logging.getLogger(__name__)


class RunnerState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class _DurationBudgetExceeded(Exception):
    """Internal signal raised when `max_duration_sec` elapses. Not an error -- the
    worker loop treats this as a graceful, intentional stop."""
    pass


class MacroRunner:
    """Coordinates background execution of an action list with pause/resume and emergency stop."""

    def __init__(self, max_duration_sec: Optional[float] = None, action_delay_sec: float = 0.0):
        self._actions: List[Action] = []
        self._state = RunnerState.IDLE
        self._thread: Optional[threading.Thread] = None
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._repeat_count: int = 1  # 0 for infinite loop
        self._state_callbacks: List[Callable[[RunnerState, str], None]] = []
        self._lock = threading.Lock()
        self._require_focus: bool = False  # Optional pre-execution focus guard
        self._max_duration_sec = max_duration_sec  # None = unlimited (prior behavior)
        self._action_delay_sec = action_delay_sec  # Optional pacing delay between actions

    def set_require_focus(self, enabled: bool) -> None:
        """Enables/disables the optional pre-execution target-window focus guard.

        When enabled, the runner calls `window_manager.ensure_target_focused()`
        before each loop iteration so actions land on the intended game/app
        instead of whatever window the user last clicked on. Off by default to
        preserve existing behavior (and to stay inert on non-Windows/test envs).
        """
        self._require_focus = enabled

    def set_max_duration(self, seconds: Optional[float]) -> None:
        """Sets/clears the runtime duration budget. `None` means unlimited (default)."""
        self._max_duration_sec = seconds

    def set_action_delay(self, seconds: float) -> None:
        """Sets the pacing delay (seconds) inserted after each atomic action."""
        self._action_delay_sec = seconds

    @property
    def state(self) -> RunnerState:
        return self._state

    def add_state_callback(self, callback: Callable[[RunnerState, str], None]) -> None:
        """Register a listener to receive state and log updates."""
        if callback not in self._state_callbacks:
            self._state_callbacks.append(callback)

    def _set_state(self, new_state: RunnerState, message: str = "") -> None:
        self._state = new_state
        logger.info("Runner state changed: %s (%s)", new_state.value, message)
        for cb in self._state_callbacks:
            try:
                cb(new_state, message)
            except Exception as e:
                logger.error("State callback error: %s", e)

    def load_actions(self, actions: List[Action], repeat_count: int = 1) -> None:
        """Loads actions into the runner queue."""
        self._actions = list(actions)
        self._repeat_count = repeat_count

    def start(self) -> bool:
        """Starts macro execution in a background thread."""
        with self._lock:
            if self._state == RunnerState.RUNNING:
                logger.warning("Macro is already running.")
                return False

            if not self._actions:
                logger.warning("Cannot start: no actions loaded.")
                return False

            global_safety.reset()
            self._pause_event.set()
            self._thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._thread.start()
            return True

    def pause(self) -> None:
        """Pauses execution after current atomic action."""
        if self._state == RunnerState.RUNNING:
            self._pause_event.clear()
            self._set_state(RunnerState.PAUSED, "Macro paused by user")

    def resume(self) -> None:
        """Resumes paused execution."""
        if self._state == RunnerState.PAUSED:
            self._pause_event.set()
            self._set_state(RunnerState.RUNNING, "Macro resumed")

    def stop(self, reason: str = "Stopped by user") -> None:
        """Stops execution and releases all inputs."""
        global_safety.trigger_killswitch(reason)
        self._pause_event.set()
        self._set_state(RunnerState.STOPPED, reason)

    def _worker_loop(self) -> None:
        """Background worker thread executing action sequence."""
        self._set_state(RunnerState.RUNNING, f"Executing {len(self._actions)} actions")
        loop_iteration = 0
        run_start_time = time.time()

        try:
            while True:
                # Check killswitch
                global_safety.assert_safe()

                # Handle pause
                self._pause_event.wait()
                global_safety.assert_safe()

                loop_iteration += 1
                logger.debug("Starting macro loop iteration %d", loop_iteration)

                # Optional pre-execution guard: refocus the target window before
                # dispatching this iteration's actions. Best-effort -- a failed
                # refocus is logged but does not abort the macro, since the
                # killswitch/pause checks above already guard user safety.
                if self._require_focus and not window_manager.ensure_target_focused():
                    logger.warning("Could not confirm target window focus before iteration %d", loop_iteration)

                for idx, action in enumerate(self._actions):
                    global_safety.assert_safe()
                    self._pause_event.wait()
                    global_safety.assert_safe()

                    # Runtime duration budget: halt gracefully before starting the
                    # next atomic action once the allotted time ceiling is reached.
                    if self._max_duration_sec is not None and (time.time() - run_start_time) >= self._max_duration_sec:
                        raise _DurationBudgetExceeded(
                            f"Max duration of {self._max_duration_sec}s reached"
                        )

                    # Execute atomic action, benchmarking duration for telemetry.
                    action_started = time.time()
                    try:
                        action.execute()
                    except Exception as e:
                        history_recorder.record(
                            action_type=getattr(action, "action_type", type(action).__name__),
                            details=str(action),
                            duration_ms=(time.time() - action_started) * 1000.0,
                            status="error",
                            error_msg=str(e),
                        )
                        raise
                    else:
                        history_recorder.record(
                            action_type=getattr(action, "action_type", type(action).__name__),
                            details=str(action),
                            duration_ms=(time.time() - action_started) * 1000.0,
                            status="success",
                        )

                    if self._action_delay_sec > 0:
                        time.sleep(self._action_delay_sec)

                # Check repeat condition
                if self._repeat_count > 0 and loop_iteration >= self._repeat_count:
                    break

            self._set_state(RunnerState.IDLE, "Macro completed successfully")

        except _DurationBudgetExceeded as e:
            logger.info("Worker loop halted by duration budget: %s", e)
            self._set_state(RunnerState.IDLE, str(e))
        except EmergencyStopTriggered as e:
            logger.warning("Worker loop stopped by killswitch: %s", e)
            self._set_state(RunnerState.STOPPED, "Emergency Killswitch Activated")
        except Exception as e:
            logger.error("Unexpected error in worker loop: %s", e, exc_info=True)
            self._set_state(RunnerState.STOPPED, f"Error: {e}")
        finally:
            if self._state != RunnerState.STOPPED and self._state != RunnerState.IDLE:
                self._set_state(RunnerState.IDLE, "Execution ended")


# Global macro runner instance
runner = MacroRunner()

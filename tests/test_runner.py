"""Unit tests for the macro execution runner."""

import time
import robex.engine.runner as runner_module
from robex.engine.runner import MacroRunner, RunnerState
from robex.engine.actions import Action
from robex.engine.history import HistoryRecorder


class MockAction(Action):
    executed: bool = False
    action_type: str = "mock"

    def __init__(self):
        # Action's inherited dataclass __init__ would otherwise reset action_type
        # back to the base "base" default, so set it explicitly here.
        self.action_type = "mock"
        self.executed = False

    def execute(self) -> None:
        self.executed = True


class SlowMockAction(Action):
    """A mock action that takes a small, deterministic amount of time to execute."""
    action_type: str = "slow_mock"
    run_count: int = 0

    def __init__(self, sleep_sec: float = 0.02):
        self.action_type = "slow_mock"
        self.sleep_sec = sleep_sec
        self.run_count = 0

    def execute(self) -> None:
        time.sleep(self.sleep_sec)
        self.run_count += 1


class FailingMockAction(Action):
    """A mock action that always raises, to exercise the error-recording path."""
    action_type: str = "failing_mock"

    def __init__(self):
        self.action_type = "failing_mock"

    def execute(self) -> None:
        raise RuntimeError("mock action failure")


def test_runner_execution_and_completion():
    runner = MacroRunner()
    action1 = MockAction()
    action2 = MockAction()

    runner.load_actions([action1, action2], repeat_count=1)
    assert runner.state == RunnerState.IDLE

    started = runner.start()
    assert started

    # Wait for execution to finish
    time.sleep(0.15)
    assert runner.state == RunnerState.IDLE
    assert action1.executed
    assert action2.executed


def test_runner_stop():
    runner = MacroRunner()
    action = MockAction()
    runner.load_actions([action], repeat_count=10)

    runner.start()
    runner.stop("Test stop")

    assert runner.state == RunnerState.STOPPED


def test_runner_records_action_history(monkeypatch):
    fresh_history = HistoryRecorder()
    monkeypatch.setattr(runner_module, "history_recorder", fresh_history)

    runner = MacroRunner()
    action1 = MockAction()
    action2 = MockAction()
    runner.load_actions([action1, action2], repeat_count=1)

    runner.start()
    time.sleep(0.15)

    records = fresh_history.get_records()
    assert len(records) == 2
    assert all(r.status == "success" for r in records)
    assert all(r.action_type == "mock" for r in records)
    assert all(r.duration_ms >= 0.0 for r in records)


def test_runner_records_error_status_on_action_failure(monkeypatch):
    fresh_history = HistoryRecorder()
    monkeypatch.setattr(runner_module, "history_recorder", fresh_history)

    runner = MacroRunner()
    runner.load_actions([FailingMockAction()], repeat_count=1)

    runner.start()
    time.sleep(0.15)

    records = fresh_history.get_records()
    assert len(records) == 1
    assert records[0].status == "error"
    assert "mock action failure" in records[0].error_msg
    assert runner.state == RunnerState.STOPPED


def test_runner_max_duration_halts_gracefully():
    runner = MacroRunner(max_duration_sec=0.05)
    action = SlowMockAction(sleep_sec=0.02)
    # Infinite repeat -- without the duration budget this would never stop on its own.
    runner.load_actions([action], repeat_count=0)

    runner.start()
    time.sleep(0.5)

    assert runner.state == RunnerState.IDLE
    assert action.run_count > 0


def test_runner_max_duration_none_behaves_like_before():
    runner = MacroRunner()
    action = MockAction()
    runner.load_actions([action], repeat_count=1)

    runner.start()
    time.sleep(0.15)

    assert runner.state == RunnerState.IDLE
    assert action.executed


def test_runner_action_delay_sec_paces_execution():
    runner = MacroRunner(action_delay_sec=0.05)
    action1 = SlowMockAction(sleep_sec=0.0)
    action2 = SlowMockAction(sleep_sec=0.0)
    runner.load_actions([action1, action2], repeat_count=1)

    start = time.time()
    runner.start()

    deadline = start + 2.0
    while runner.state != RunnerState.IDLE and time.time() < deadline:
        time.sleep(0.01)
    elapsed = time.time() - start

    assert action1.run_count == 1
    assert action2.run_count == 1
    # Two actions with a 0.05s pacing delay after each should take at least ~0.1s.
    assert elapsed >= 0.09

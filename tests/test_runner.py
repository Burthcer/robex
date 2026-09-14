"""Unit tests for the macro execution runner."""

import time
from robex.engine.runner import MacroRunner, RunnerState
from robex.engine.actions import Action


class MockAction(Action):
    executed: bool = False
    action_type: str = "mock"

    def execute(self) -> None:
        self.executed = True


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

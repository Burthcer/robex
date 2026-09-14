# Task 4: Execution Telemetry, Action History & Runtime Constraints

## Objective
Build a thread-safe execution history recorder with JSON export and integrate runtime duration budgets into the macro runner, operating strictly within 5 MB RAM and 0 GB VRAM.

## Target Files
- `src/robex/engine/history.py` [NEW]
- `src/robex/engine/runner.py` [MODIFY]
- `src/robex/engine/__init__.py` [MODIFY]
- `tests/test_history.py` [NEW]
- `tests/test_runner.py` [MODIFY]

## Actionable Checklist
1. Create `src/robex/engine/history.py` implementing an `ActionRecord` dataclass (action_type, details, timestamp, duration_ms, status, error_msg) and a thread-safe `HistoryRecorder` maintaining a fixed-size ring buffer (maximum 1,000 entries) to prevent unbounded memory growth.
2. Implement summary metrics (`get_summary() -> HistorySummary`) and structured JSON serialization (`export_to_json(filepath)`) in `HistoryRecorder` so users can inspect past execution logs and durations.
3. Extend `MacroRunner` in `src/robex/engine/runner.py` with runtime budget controls (`max_duration_sec: Optional[float]` and `action_delay_sec: float = 0.0`) that automatically halt execution gracefully when the allotted time ceiling expires.
4. Update `_worker_loop` in `src/robex/engine/runner.py` to benchmark each action's execution duration, append structured telemetry records to `history_recorder`, and enforce `max_duration_sec` checks before each atomic step.
5. Author comprehensive unit tests in `tests/test_history.py` and expand `tests/test_runner.py` verifying accurate duration tracking, thread safety, JSON export, ring-buffer bounding, and max-duration enforcement.

## Constraints
- **Strict Resource Budget**: History storage must be capped at 1,000 items in memory; total RAM overhead must remain below 5 MB with 0 GB VRAM consumption to adhere strictly to the 4 GB ceilings.
- **Documentation Integrity**: Preserve all existing comments, docstrings, and architectural structure in `src/robex/engine/runner.py`.
- **Backward Compatibility**: When `max_duration_sec` is `None`, runner must behave identically to previous iterations; all 53 existing unit tests must continue to pass without error.

## Verification Command
```powershell
.\venv\Scripts\pytest tests/test_history.py tests/test_runner.py tests/ -v
```

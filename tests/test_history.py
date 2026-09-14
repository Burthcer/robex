"""Unit tests for the execution history recorder: ring buffer, summary, JSON export, threading."""

import json
import os
import tempfile
import threading

from robex.engine.history import HistoryRecorder, ActionRecord, HistorySummary


def test_record_appends_action_record():
    recorder = HistoryRecorder()
    recorder.record(action_type="click", details="ClickAction(x=1,y=2)", duration_ms=12.5, status="success")

    records = recorder.get_records()
    assert len(records) == 1
    assert isinstance(records[0], ActionRecord)
    assert records[0].action_type == "click"
    assert records[0].duration_ms == 12.5
    assert records[0].status == "success"
    assert records[0].error_msg is None
    assert records[0].timestamp > 0


def test_record_error_captures_error_msg():
    recorder = HistoryRecorder()
    recorder.record(action_type="click", status="error", error_msg="boom")

    records = recorder.get_records()
    assert records[0].status == "error"
    assert records[0].error_msg == "boom"


def test_ring_buffer_bounds_to_max_entries():
    recorder = HistoryRecorder(max_entries=5)
    for i in range(10):
        recorder.record(action_type=f"action_{i}")

    records = recorder.get_records()
    assert len(records) == 5
    # Oldest entries (0-4) must have been evicted; only the last 5 remain, oldest-first.
    assert [r.action_type for r in records] == [f"action_{i}" for i in range(5, 10)]


def test_default_max_entries_is_1000():
    recorder = HistoryRecorder()
    for i in range(1200):
        recorder.record(action_type="tick")

    assert len(recorder.get_records()) == 1000


def test_clear_empties_history():
    recorder = HistoryRecorder()
    recorder.record(action_type="click")
    recorder.clear()
    assert recorder.get_records() == []


def test_get_summary_computes_aggregate_metrics():
    recorder = HistoryRecorder()
    recorder.record(action_type="click", duration_ms=10.0, status="success")
    recorder.record(action_type="wait", duration_ms=20.0, status="success")
    recorder.record(action_type="click", duration_ms=5.0, status="error", error_msg="x")

    summary = recorder.get_summary()
    assert isinstance(summary, HistorySummary)
    assert summary.total_actions == 3
    assert summary.success_count == 2
    assert summary.error_count == 1
    assert summary.total_duration_ms == 35.0
    assert abs(summary.avg_duration_ms - (35.0 / 3)) < 1e-9


def test_get_summary_empty_history_has_zero_average():
    recorder = HistoryRecorder()
    summary = recorder.get_summary()
    assert summary.total_actions == 0
    assert summary.avg_duration_ms == 0.0


def test_export_to_json_writes_summary_and_records():
    recorder = HistoryRecorder()
    recorder.record(action_type="click", details="d", duration_ms=1.5, status="success")

    with tempfile.TemporaryDirectory() as tmp_dir:
        filepath = os.path.join(tmp_dir, "history.json")
        assert recorder.export_to_json(filepath) is True

        with open(filepath, "r", encoding="utf-8") as f:
            payload = json.load(f)

        assert payload["summary"]["total_actions"] == 1
        assert len(payload["records"]) == 1
        assert payload["records"][0]["action_type"] == "click"
        assert payload["records"][0]["duration_ms"] == 1.5


def test_export_to_json_invalid_path_returns_false():
    recorder = HistoryRecorder()
    recorder.record(action_type="click")
    # A directory path that cannot be opened for writing as a file.
    assert recorder.export_to_json(os.path.join("nonexistent_dir_xyz", "sub", "history.json")) is False


def test_record_is_thread_safe():
    recorder = HistoryRecorder(max_entries=10000)
    thread_count = 20
    records_per_thread = 100

    def worker():
        for _ in range(records_per_thread):
            recorder.record(action_type="tick")

    threads = [threading.Thread(target=worker) for _ in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(recorder.get_records()) == thread_count * records_per_thread

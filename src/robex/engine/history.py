"""Thread-safe execution history recorder with a bounded ring buffer and JSON export.

Tracks what the macro runner actually did -- per-action timing, status, and errors --
so users can inspect past runs. Storage is a fixed-size ring buffer (default 1,000
entries) so long-running/looping macros never grow memory unbounded.
"""

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Deque, List, Optional

logger = logging.getLogger(__name__)

MAX_HISTORY_ENTRIES = 1000


@dataclass
class ActionRecord:
    """A single recorded action execution."""
    action_type: str
    details: str
    timestamp: float
    duration_ms: float
    status: str  # "success" or "error"
    error_msg: Optional[str] = None


@dataclass
class HistorySummary:
    """Aggregate metrics computed over the currently recorded history."""
    total_actions: int
    success_count: int
    error_count: int
    total_duration_ms: float
    avg_duration_ms: float


class HistoryRecorder:
    """Records `ActionRecord` entries in a thread-safe, fixed-size ring buffer."""

    def __init__(self, max_entries: int = MAX_HISTORY_ENTRIES):
        self._max_entries = max_entries
        # deque(maxlen=...) silently evicts the oldest entry once full, which is
        # exactly the bounded-memory ring-buffer behavior required here.
        self._records: Deque[ActionRecord] = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def record(
        self,
        action_type: str,
        details: str = "",
        duration_ms: float = 0.0,
        status: str = "success",
        error_msg: Optional[str] = None,
    ) -> None:
        """Appends a new record, evicting the oldest entry once at capacity."""
        entry = ActionRecord(
            action_type=action_type,
            details=details,
            timestamp=time.time(),
            duration_ms=duration_ms,
            status=status,
            error_msg=error_msg,
        )
        with self._lock:
            self._records.append(entry)

    def get_records(self) -> List[ActionRecord]:
        """Returns a snapshot copy of all currently recorded entries, oldest first."""
        with self._lock:
            return list(self._records)

    def clear(self) -> None:
        """Clears all recorded history."""
        with self._lock:
            self._records.clear()

    def get_summary(self) -> HistorySummary:
        """Computes aggregate metrics (counts, durations) over the recorded history."""
        with self._lock:
            records = list(self._records)

        total = len(records)
        success = sum(1 for r in records if r.status == "success")
        errors = total - success
        total_duration = sum(r.duration_ms for r in records)
        avg_duration = (total_duration / total) if total else 0.0

        return HistorySummary(
            total_actions=total,
            success_count=success,
            error_count=errors,
            total_duration_ms=total_duration,
            avg_duration_ms=avg_duration,
        )

    def export_to_json(self, filepath: str) -> bool:
        """Serializes the current summary + records to a JSON file. Returns True on success."""
        payload = {
            "summary": asdict(self.get_summary()),
            "records": [asdict(r) for r in self.get_records()],
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            return True
        except OSError as e:
            logger.error("Failed to export history to '%s': %s", filepath, e)
            return False


# Global history recorder instance
history_recorder = HistoryRecorder()

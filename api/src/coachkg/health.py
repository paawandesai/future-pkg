"""Last-success times for /healthz, kept in memory per process. Nothing here calls a model."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

_lock = threading.Lock()
_times: dict[str, str | None] = {
    "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
    "last_model_call_ok_at": None,
    "last_plan_saved_at": None,
}


def mark(name: str) -> None:
    with _lock:
        _times[name] = datetime.now(UTC).isoformat(timespec="seconds")


def snapshot() -> dict[str, str | None]:
    with _lock:
        return dict(_times)

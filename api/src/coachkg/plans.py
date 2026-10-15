"""Plan storage. A plan is a draft until the coach confirms it; nothing is member-facing before.

SQLite locally. The deployed stack swaps in a DynamoDB store with the same methods.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol


class PlanStore(Protocol):
    def save(self, plan: dict[str, Any]) -> None: ...
    def get(self, plan_id: str) -> dict[str, Any] | None: ...
    def confirm(self, plan_id: str, coach_id: str) -> dict[str, Any] | None: ...


class SqlitePlanStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, member_id TEXT, coach_id TEXT,"
            " status TEXT, created_at TEXT, confirmed_at TEXT, body TEXT)"
        )
        self._db.commit()

    def save(self, plan: dict[str, Any]) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO plans VALUES (?, ?, ?, ?, ?, NULL, ?)",
                (
                    plan["id"],
                    plan["member_id"],
                    plan["coach_id"],
                    plan["status"],
                    plan["created_at"],
                    json.dumps(plan),
                ),
            )
            self._db.commit()

    def get(self, plan_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT body FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if row is None:
            return None
        plan: dict[str, Any] = json.loads(row[0])
        return plan

    def confirm(self, plan_id: str, coach_id: str) -> dict[str, Any] | None:
        plan = self.get(plan_id)
        if plan is None or plan["coach_id"] != coach_id:
            return None
        if plan["status"] != "confirmed":
            plan["status"] = "confirmed"
            plan["confirmed_at"] = datetime.now(UTC).isoformat(timespec="seconds")
            plan["confirmed_by"] = coach_id
            with self._lock:
                self._db.execute(
                    "UPDATE plans SET status = ?, confirmed_at = ?, body = ? WHERE id = ?",
                    ("confirmed", plan["confirmed_at"], json.dumps(plan), plan_id),
                )
                self._db.commit()
        return plan

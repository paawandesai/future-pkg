"""Plan storage. A plan is a draft until the coach confirms it; nothing is member-facing before.

SQLite locally. The deployed stack uses DynamoDB (PLAN_TABLE); every item carries an
`expires_at` TTL, and a scheduled purge job deletes anything older than a day.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
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


PLAN_TTL = timedelta(days=1)


class DynamoPlanStore:
    """Plans as items keyed by id; the plan body is stored as JSON text, so no float/Decimal mapping."""

    def __init__(self, table: Any) -> None:
        self._table = table

    @classmethod
    def from_env(cls, table_name: str) -> DynamoPlanStore:
        import boto3  # type: ignore[import-not-found]  # provided by the Lambda runtime

        return cls(boto3.resource("dynamodb").Table(table_name))

    def save(self, plan: dict[str, Any]) -> None:
        expires = int((datetime.now(UTC) + PLAN_TTL).timestamp())
        self._table.put_item(
            Item={
                "id": plan["id"],
                "coach_id": plan["coach_id"],
                "member_id": plan["member_id"],
                "status": plan["status"],
                "created_at": plan["created_at"],
                "expires_at": expires,
                "body": json.dumps(plan),
            },
            ConditionExpression="attribute_not_exists(id)",
        )

    def get(self, plan_id: str) -> dict[str, Any] | None:
        item = self._table.get_item(Key={"id": plan_id}, ConsistentRead=True).get("Item")
        # TTL deletes expired items only eventually, so an expired plan is treated as gone.
        if item is None or int(item.get("expires_at", 0)) <= datetime.now(UTC).timestamp():
            return None
        plan: dict[str, Any] = json.loads(item["body"])
        return plan

    def confirm(self, plan_id: str, coach_id: str) -> dict[str, Any] | None:
        plan = self.get(plan_id)
        if plan is None or plan["coach_id"] != coach_id:
            return None
        if plan["status"] != "confirmed":
            plan["status"] = "confirmed"
            plan["confirmed_at"] = datetime.now(UTC).isoformat(timespec="seconds")
            plan["confirmed_by"] = coach_id
            self._table.update_item(
                Key={"id": plan_id},
                UpdateExpression="SET #s = :s, body = :b",
                ConditionExpression="coach_id = :c",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":s": "confirmed", ":b": json.dumps(plan), ":c": coach_id},
            )
        return plan

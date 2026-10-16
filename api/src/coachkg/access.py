"""Demo access: requests for an account, and the admin actions that invite or disable reviewers.

Nobody gets an account without an admin approving it. A request holds an email, an optional name
and a short reason; it expires after REQUEST_TTL and is never logged. Requests are rate-limited
per client (by a salted hash of the address, never the address itself) and capped in total, so
the public form can't be used to flood the table or the admin.

Locally (mock auth) everything lives in memory and "inviting" sends nothing. Deployed, requests
live in DynamoDB (ACCESS_TABLE) and accounts in the Cognito pool (COGNITO_USER_POOL_ID); Cognito
emails the temporary password itself, so no password ever passes through this code.
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, field_validator

REQUEST_TTL = timedelta(days=7)
MAX_PENDING = 50
PER_CLIENT_PER_HOUR = 3
DEMO_COACH = "coach_01HXSAM"
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[A-Za-z]{2,}$")

Status = Literal["pending", "approved", "rejected"]


class AccessRequestIn(BaseModel):
    email: str = Field(min_length=6, max_length=254)
    name: str = Field(default="", max_length=80)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL.match(v):
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("name", "reason")
    @classmethod
    def _strip(cls, v: str) -> str:
        return " ".join(v.split())


class AccessRequest(BaseModel):
    id: str
    email: str
    name: str
    reason: str
    status: Status
    created_at: str
    decided_by: str | None = None
    decided_at: str | None = None


class RateLimited(Exception):
    """Too many requests from one client, or too many pending in total."""


def client_key(address: str | None) -> str:
    salt = os.environ.get("RATE_SALT", "local")
    return hashlib.sha256(f"{salt}:{address or 'unknown'}".encode()).hexdigest()[:32]


def _now() -> datetime:
    return datetime.now(UTC)


class AccessStore(Protocol):
    def submit(self, req: AccessRequestIn, client: str) -> None: ...
    def list(self) -> list[AccessRequest]: ...
    def get(self, request_id: str) -> AccessRequest | None: ...
    def decide(self, request_id: str, status: Status, by: str) -> AccessRequest | None: ...


@dataclass
class MemoryAccessStore:
    requests: dict[str, AccessRequest] = field(default_factory=dict)
    hits: dict[str, int] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def submit(self, req: AccessRequestIn, client: str) -> None:
        with self.lock:
            bucket = f"{client}:{_now():%Y%m%d%H}"
            self.hits[bucket] = self.hits.get(bucket, 0) + 1
            if self.hits[bucket] > PER_CLIENT_PER_HOUR:
                raise RateLimited
            pending = [r for r in self.requests.values() if r.status == "pending"]
            if any(r.email == req.email for r in pending):
                return  # same answer as a new request, so the form doesn't reveal who asked
            if len(pending) >= MAX_PENDING:
                raise RateLimited
            rid = uuid.uuid4().hex
            self.requests[rid] = AccessRequest(
                id=rid, status="pending", created_at=_now().isoformat(timespec="seconds"), **req.model_dump()
            )

    def list(self) -> list[AccessRequest]:
        return sorted(self.requests.values(), key=lambda r: r.created_at, reverse=True)

    def get(self, request_id: str) -> AccessRequest | None:
        return self.requests.get(request_id)

    def decide(self, request_id: str, status: Status, by: str) -> AccessRequest | None:
        with self.lock:
            r = self.requests.get(request_id)
            if r is None or r.status != "pending":
                return None
            r = r.model_copy(
                update={
                    "status": status,
                    "decided_by": by,
                    "decided_at": _now().isoformat(timespec="seconds"),
                }
            )
            self.requests[request_id] = r
            return r


class DynamoAccessStore:
    """One table: request items (`id` = uuid) and hourly rate counters (`id` = rate#<key>#<hour>)."""

    def __init__(self, table: Any) -> None:
        self._t = table

    @classmethod
    def from_env(cls, table_name: str) -> DynamoAccessStore:
        import boto3  # type: ignore[import-not-found]  # provided by the Lambda runtime

        return cls(boto3.resource("dynamodb").Table(table_name))

    def _requests(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        kw: dict[str, Any] = {"FilterExpression": "kind = :k", "ExpressionAttributeValues": {":k": "request"}}
        while True:
            page = self._t.scan(**kw)
            items += page.get("Items", [])
            if "LastEvaluatedKey" not in page:
                return items
            kw["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def submit(self, req: AccessRequestIn, client: str) -> None:
        now = _now()
        hour = int((now + timedelta(hours=2)).timestamp())
        hits = self._t.update_item(
            Key={"id": f"rate#{client}#{now:%Y%m%d%H}"},
            UpdateExpression="ADD hits :one SET expires_at = :e, kind = :k",
            ExpressionAttributeValues={":one": 1, ":e": hour, ":k": "rate"},
            ReturnValues="UPDATED_NEW",
        )["Attributes"]["hits"]
        if int(hits) > PER_CLIENT_PER_HOUR:
            raise RateLimited
        pending = [i for i in self._requests() if i.get("status") == "pending"]
        if any(i.get("email") == req.email for i in pending):
            return
        if len(pending) >= MAX_PENDING:
            raise RateLimited
        self._t.put_item(
            Item={
                "id": uuid.uuid4().hex,
                "kind": "request",
                "status": "pending",
                "created_at": now.isoformat(timespec="seconds"),
                "expires_at": int((now + REQUEST_TTL).timestamp()),
                **req.model_dump(),
            }
        )

    @staticmethod
    def _model(item: dict[str, Any]) -> AccessRequest:
        return AccessRequest.model_validate(
            {k: v for k, v in item.items() if k not in ("kind", "expires_at")}
        )

    def list(self) -> list[AccessRequest]:
        return sorted((self._model(i) for i in self._requests()), key=lambda r: r.created_at, reverse=True)

    def get(self, request_id: str) -> AccessRequest | None:
        item = self._t.get_item(Key={"id": request_id}, ConsistentRead=True).get("Item")
        return self._model(item) if item and item.get("kind") == "request" else None

    def decide(self, request_id: str, status: Status, by: str) -> AccessRequest | None:
        try:
            item = self._t.update_item(
                Key={"id": request_id},
                UpdateExpression="SET #s = :s, decided_by = :b, decided_at = :a",
                ConditionExpression="kind = :k AND #s = :p",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":s": status,
                    ":b": by,
                    ":a": _now().isoformat(timespec="seconds"),
                    ":k": "request",
                    ":p": "pending",
                },
                ReturnValues="ALL_NEW",
            )["Attributes"]
        except self._t.meta.client.exceptions.ConditionalCheckFailedException:
            return None
        return self._model(item)


# ---------- accounts ----------


class DemoUser(BaseModel):
    email: str
    status: str
    enabled: bool
    admin: bool
    created_at: str | None = None


class Accounts(Protocol):
    def invite(self, email: str, coach_id: str = DEMO_COACH) -> None: ...
    def list(self) -> list[DemoUser]: ...
    def disable(self, email: str) -> None: ...
    def enable(self, email: str) -> None: ...


class AccountExists(Exception):
    pass


@dataclass
class MemoryAccounts:
    """Local stand-in: records invites, sends nothing."""

    users: dict[str, DemoUser] = field(default_factory=dict)

    def invite(self, email: str, coach_id: str = DEMO_COACH) -> None:
        if email in self.users:
            raise AccountExists
        self.users[email] = DemoUser(
            email=email,
            status="invited (local: no email sent)",
            enabled=True,
            admin=False,
            created_at=_now().isoformat(timespec="seconds"),
        )

    def list(self) -> list[DemoUser]:
        return list(self.users.values())

    def disable(self, email: str) -> None:
        if email in self.users:
            self.users[email] = self.users[email].model_copy(update={"enabled": False})

    def enable(self, email: str) -> None:
        if email in self.users:
            self.users[email] = self.users[email].model_copy(update={"enabled": True})


class CognitoAccounts:
    def __init__(self, client: Any, pool_id: str) -> None:
        self._c = client
        self._pool = pool_id

    @classmethod
    def from_env(cls, pool_id: str) -> CognitoAccounts:
        import boto3  # provided by the Lambda runtime

        return cls(boto3.client("cognito-idp"), pool_id)

    def invite(self, email: str, coach_id: str = DEMO_COACH) -> None:
        try:
            self._c.admin_create_user(
                UserPoolId=self._pool,
                Username=email,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                    {"Name": "custom:coach_id", "Value": coach_id},
                ],
                DesiredDeliveryMediums=["EMAIL"],
            )
        except self._c.exceptions.UsernameExistsException:
            raise AccountExists from None

    def _admins(self) -> set[str]:
        out: set[str] = set()
        kw: dict[str, Any] = {}
        while True:
            page = self._c.list_users_in_group(UserPoolId=self._pool, GroupName="admin", **kw)
            out |= {u["Username"] for u in page["Users"]}
            if "NextToken" not in page:
                return out
            kw = {"NextToken": page["NextToken"]}

    def list(self) -> list[DemoUser]:
        admins = self._admins()
        users: list[DemoUser] = []
        kw: dict[str, Any] = {}
        while True:
            page = self._c.list_users(UserPoolId=self._pool, **kw)
            for u in page["Users"]:
                email = next((a["Value"] for a in u.get("Attributes", []) if a["Name"] == "email"), "")
                created = u.get("UserCreateDate")
                users.append(
                    DemoUser(
                        email=email,
                        status=str(u.get("UserStatus", "")),
                        enabled=bool(u.get("Enabled")),
                        admin=u["Username"] in admins,
                        created_at=created.isoformat(timespec="seconds") if created else None,
                    )
                )
            if "PaginationToken" not in page:
                return sorted(users, key=lambda x: x.created_at or "", reverse=True)
            kw = {"PaginationToken": page["PaginationToken"]}

    def disable(self, email: str) -> None:
        self._c.admin_disable_user(UserPoolId=self._pool, Username=email)

    def enable(self, email: str) -> None:
        self._c.admin_enable_user(UserPoolId=self._pool, Username=email)

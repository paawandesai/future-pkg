"""Demo access: requests for an account, and the admin actions that invite or disable reviewers.

Nobody gets an account without an admin approving it. A request holds an email, an optional name
and a short reason; it expires after REQUEST_TTL and is never logged. An expired request is gone
for every purpose: it isn't listed, counted or approvable, even before DynamoDB's TTL removes it.
Requests are rate-limited per client (by a salted hash of the viewer address, never the address
itself) and capped in total, so the public form can't be used to flood the table or the admin; an
admin can reject every pending request at once if the cap fills.

Locally (mock auth) everything lives in memory and "inviting" sends nothing. Deployed, requests
live in DynamoDB (ACCESS_TABLE) and accounts in the Cognito pool (COGNITO_USER_POOL_ID); Cognito
emails the temporary password itself, so no password ever passes through this code.
"""

from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import threading
import unicodedata
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
# Sparse index on `status`: only request items have one (rate counters don't), so the pending
# requests can be read with a query instead of a table scan.
PENDING_INDEX = "by-status"


def _no_control_chars(v: str) -> str:
    """Refuse NUL and other control characters, and format characters such as bidi overrides,
    which could make an email or reason read differently to the admin than it is stored."""
    if any(unicodedata.category(c) in ("Cc", "Cf") and c not in "\t\n\r" for c in v):
        raise ValueError("Remove the control or formatting characters")
    return v


def normalise_email(v: str) -> str:
    v = _no_control_chars(v).strip().lower()
    if not EMAIL.match(v):
        raise ValueError("Enter a valid email address")
    return v


class AccessRequestIn(BaseModel):
    email: str = Field(min_length=6, max_length=254)
    name: str = Field(default="", max_length=80)
    reason: str = Field(min_length=3, max_length=500)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalise_email(v)

    @field_validator("name", "reason")
    @classmethod
    def _strip(cls, v: str) -> str:
        return " ".join(_no_control_chars(v).split())


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


def viewer_network(header: str | None) -> str | None:
    """The viewer from CloudFront-Viewer-Address ("ip:port", IPv6 without brackets), which CloudFront
    sets itself. IPv6 is keyed by its /64, since one subscriber usually holds a whole /64."""
    host = (header or "").strip().rsplit(":", 1)[0].strip("[]")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return None
    return str(ipaddress.ip_network(f"{ip}/64", strict=False)) if ip.version == 6 else str(ip)


def client_key(address: str | None) -> str:
    salt = os.environ.get("RATE_SALT", "local")
    return hashlib.sha256(f"{salt}:{address or 'unknown'}".encode()).hexdigest()[:32]


def _now() -> datetime:
    return datetime.now(UTC)


def _live(r: AccessRequest) -> bool:
    return datetime.fromisoformat(r.created_at) + REQUEST_TTL > _now()


class AccessStore(Protocol):
    def submit(self, req: AccessRequestIn, client: str) -> None: ...
    def list(self) -> list[AccessRequest]: ...
    def get(self, request_id: str) -> AccessRequest | None: ...
    def decide(self, request_id: str, status: Status, by: str) -> AccessRequest | None: ...
    def reject_pending(self, by: str) -> int: ...


@dataclass
class MemoryAccessStore:
    requests: dict[str, AccessRequest] = field(default_factory=dict)
    hits: dict[str, int] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def submit(self, req: AccessRequestIn, client: str) -> None:
        with self.lock:
            # The total cap is checked before the per-client counter, so a full queue costs nothing.
            pending = [r for r in self.requests.values() if r.status == "pending" and _live(r)]
            if any(r.email == req.email for r in pending):
                return  # same answer as a new request, so the form doesn't reveal who asked
            if len(pending) >= MAX_PENDING:
                raise RateLimited
            bucket = f"{client}:{_now():%Y%m%d%H}"
            self.hits[bucket] = self.hits.get(bucket, 0) + 1
            if self.hits[bucket] > PER_CLIENT_PER_HOUR:
                raise RateLimited
            rid = uuid.uuid4().hex
            self.requests[rid] = AccessRequest(
                id=rid, status="pending", created_at=_now().isoformat(timespec="seconds"), **req.model_dump()
            )

    def list(self) -> list[AccessRequest]:
        live = (r for r in self.requests.values() if _live(r))
        return sorted(live, key=lambda r: r.created_at, reverse=True)

    def get(self, request_id: str) -> AccessRequest | None:
        r = self.requests.get(request_id)
        return r if r is not None and _live(r) else None

    def decide(self, request_id: str, status: Status, by: str) -> AccessRequest | None:
        with self.lock:
            r = self.requests.get(request_id)
            if r is None or r.status != "pending" or not _live(r):
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

    def reject_pending(self, by: str) -> int:
        pending = [r.id for r in self.list() if r.status == "pending"]
        return sum(self.decide(rid, "rejected", by) is not None for rid in pending)


class DynamoAccessStore:
    """One table: request items (`id` = uuid) and hourly rate counters (`id` = rate#<key>#<hour>).

    Every read filters on `expires_at`, because DynamoDB's TTL deletes expired items only eventually.
    """

    def __init__(self, table: Any) -> None:
        self._t = table

    @classmethod
    def from_env(cls, table_name: str) -> DynamoAccessStore:
        import boto3  # type: ignore[import-not-found]  # provided by the Lambda runtime

        return cls(boto3.resource("dynamodb").Table(table_name))

    @staticmethod
    def _pages(call: Any, **kw: Any) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        while True:
            page = call(**kw)
            items += page.get("Items", [])
            if "LastEvaluatedKey" not in page:
                return items
            kw["ExclusiveStartKey"] = page["LastEvaluatedKey"]

    def _requests(self) -> list[dict[str, Any]]:
        """Every unexpired request (admin list only; the public form never scans)."""
        return self._pages(
            self._t.scan,
            FilterExpression="kind = :k AND expires_at > :now",
            ExpressionAttributeValues={":k": "request", ":now": int(_now().timestamp())},
        )

    def _pending(self) -> list[dict[str, Any]]:
        return self._pages(
            self._t.query,
            IndexName=PENDING_INDEX,
            KeyConditionExpression="#s = :p",
            FilterExpression="expires_at > :now",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":p": "pending", ":now": int(_now().timestamp())},
        )

    def submit(self, req: AccessRequestIn, client: str) -> None:
        now = _now()
        # The total cap is checked before the per-client counter, so a full queue costs nothing.
        pending = self._pending()
        if any(i.get("email") == req.email for i in pending):
            return
        if len(pending) >= MAX_PENDING:
            raise RateLimited
        hour = int((now + timedelta(hours=2)).timestamp())
        hits = self._t.update_item(
            Key={"id": f"rate#{client}#{now:%Y%m%d%H}"},
            UpdateExpression="ADD hits :one SET expires_at = :e, kind = :k",
            ExpressionAttributeValues={":one": 1, ":e": hour, ":k": "rate"},
            ReturnValues="UPDATED_NEW",
        )["Attributes"]["hits"]
        if int(hits) > PER_CLIENT_PER_HOUR:
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
        if not item or item.get("kind") != "request" or int(item.get("expires_at", 0)) <= _now().timestamp():
            return None
        return self._model(item)

    def decide(self, request_id: str, status: Status, by: str) -> AccessRequest | None:
        try:
            item = self._t.update_item(
                Key={"id": request_id},
                UpdateExpression="SET #s = :s, decided_by = :b, decided_at = :a",
                ConditionExpression="kind = :k AND #s = :p AND expires_at > :now",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":s": status,
                    ":b": by,
                    ":a": _now().isoformat(timespec="seconds"),
                    ":k": "request",
                    ":p": "pending",
                    ":now": int(_now().timestamp()),
                },
                ReturnValues="ALL_NEW",
            )["Attributes"]
        except self._t.meta.client.exceptions.ConditionalCheckFailedException:
            return None
        return self._model(item)

    def reject_pending(self, by: str) -> int:
        return sum(self.decide(str(i["id"]), "rejected", by) is not None for i in self._pending())


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

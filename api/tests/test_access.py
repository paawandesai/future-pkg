"""Demo access: public request form, admin-only approval, and the stores behind them."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from coachkg import auth
from coachkg.access import (
    MAX_PENDING,
    PER_CLIENT_PER_HOUR,
    AccessRequestIn,
    DemoUser,
    DynamoAccessStore,
    MemoryAccessStore,
    MemoryAccounts,
    RateLimited,
)
from coachkg.main import app, get_access, get_accounts
from tests.test_auth import CLIENT, KEY, POOL, _id_jwt

REQ = {"email": "Reviewer@Example.com", "name": "A Reviewer", "reason": "Grading the take-home"}


@pytest.fixture
def stores() -> Iterator[tuple[MemoryAccessStore, MemoryAccounts]]:
    access, accounts = MemoryAccessStore(), MemoryAccounts()
    app.dependency_overrides[get_access] = lambda: access
    app.dependency_overrides[get_accounts] = lambda: accounts
    yield access, accounts
    app.dependency_overrides.clear()


@pytest.fixture
def cognito(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTH_MODE", "cognito")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", POOL)
    monkeypatch.setenv("COGNITO_CLIENT_ID", CLIENT)
    monkeypatch.setattr(auth, "signing_key", lambda token, issuer: KEY.public_key())
    return TestClient(app)


def _h(**claims: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {_id_jwt(**claims)}"}


ADMIN = {"cognito:groups": ["admin"], "email": "owner@example.com"}


def test_request_is_received_once_and_never_echoed(cognito: TestClient, stores: Any) -> None:
    access, _ = stores
    r = cognito.post("/api/access-requests", json=REQ)
    assert r.status_code == 202 and r.json() == {"status": "received"}
    assert cognito.post("/api/access-requests", json=REQ).json() == {"status": "received"}
    [only] = access.list()
    assert only.email == "reviewer@example.com" and only.status == "pending"


@pytest.mark.parametrize("bad", [{"email": "not-an-email"}, {"reason": ""}, {"reason": "x" * 501}])
def test_request_validation(cognito: TestClient, stores: Any, bad: dict[str, str]) -> None:
    assert cognito.post("/api/access-requests", json=REQ | bad).status_code == 422


def test_requests_are_rate_limited_per_client(cognito: TestClient, stores: Any) -> None:
    codes = [
        cognito.post(
            "/api/access-requests",
            json=REQ | {"email": f"r{i}@example.com"},
            headers={"X-Forwarded-For": "203.0.113.9"},
        ).status_code
        for i in range(PER_CLIENT_PER_HOUR + 1)
    ]
    assert codes == [202] * PER_CLIENT_PER_HOUR + [429]
    other = cognito.post("/api/access-requests", json=REQ, headers={"X-Forwarded-For": "198.51.100.1"})
    assert other.status_code == 202


def test_pending_requests_are_capped() -> None:
    store = MemoryAccessStore()
    for i in range(MAX_PENDING):
        store.submit(AccessRequestIn(email=f"r{i}@example.com", reason="grading"), f"client{i}")
    with pytest.raises(RateLimited):
        store.submit(AccessRequestIn(email="late@example.com", reason="grading"), "client-late")


def test_admin_routes_refuse_coaches(cognito: TestClient, stores: Any) -> None:
    for method, path in [
        ("get", "/api/admin/requests"),
        ("get", "/api/admin/users"),
        ("post", "/api/admin/users/disable-all"),
    ]:
        assert getattr(cognito, method)(path, headers=_h()).status_code == 403
        assert getattr(cognito, method)(path).status_code == 401
    assert cognito.get("/api/me", headers=_h()).json() == {"coach_id": "coach_01HXSAM", "admin": False}
    assert cognito.get("/api/me", headers=_h(**ADMIN)).json()["admin"] is True


def test_admin_approves_then_the_account_is_invited(cognito: TestClient, stores: Any) -> None:
    access, accounts = stores
    cognito.post("/api/access-requests", json=REQ)
    [pending] = cognito.get("/api/admin/requests", headers=_h(**ADMIN)).json()
    assert accounts.users == {}
    r = cognito.post(f"/api/admin/requests/{pending['id']}/approve", headers=_h(**ADMIN))
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert r.json()["decided_by"] == "owner@example.com"
    assert "reviewer@example.com" in accounts.users
    again = cognito.post(f"/api/admin/requests/{pending['id']}/approve", headers=_h(**ADMIN))
    assert again.status_code == 404


def test_reject_and_disable_all_keep_admins(cognito: TestClient, stores: Any) -> None:
    access, accounts = stores
    cognito.post("/api/access-requests", json=REQ)
    rid = access.list()[0].id
    assert (
        cognito.post(f"/api/admin/requests/{rid}/reject", headers=_h(**ADMIN)).json()["status"] == "rejected"
    )
    assert accounts.users == {}
    accounts.users["owner@example.com"] = DemoUser(
        email="owner@example.com", status="CONFIRMED", enabled=True, admin=True
    )
    assert (
        cognito.post("/api/admin/users", json={"email": "a@example.com"}, headers=_h(**ADMIN)).status_code
        == 201
    )
    assert (
        cognito.post("/api/admin/users", json={"email": "a@example.com"}, headers=_h(**ADMIN)).status_code
        == 409
    )
    off = cognito.post(
        "/api/admin/users/enabled", json={"email": "owner@example.com", "enabled": False}, headers=_h(**ADMIN)
    )
    assert off.status_code == 400
    assert cognito.post("/api/admin/users/disable-all", headers=_h(**ADMIN)).json() == {"disabled": 1}
    assert accounts.users["owner@example.com"].enabled and not accounts.users["a@example.com"].enabled


class FakeTable:
    """Just enough of a DynamoDB Table for DynamoAccessStore."""

    class _Exc:
        class ConditionalCheckFailedException(Exception):  # noqa: N818
            pass

    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}
        self.meta = type("M", (), {"client": type("C", (), {"exceptions": self._Exc})()})()

    def update_item(self, Key: dict[str, str], **kw: Any) -> dict[str, Any]:  # noqa: N803
        item = self.items.setdefault(Key["id"], {"id": Key["id"]})
        v = kw["ExpressionAttributeValues"]
        if kw["UpdateExpression"].startswith("ADD hits"):
            item["hits"] = item.get("hits", 0) + v[":one"]
            item["kind"] = v[":k"]
            return {"Attributes": {"hits": item["hits"]}}
        if item.get("kind") != v[":k"] or item.get("status") != v[":p"]:
            raise self._Exc.ConditionalCheckFailedException
        item.update(status=v[":s"], decided_by=v[":b"], decided_at=v[":a"])
        return {"Attributes": dict(item)}

    def scan(self, **kw: Any) -> dict[str, Any]:
        return {"Items": [dict(i) for i in self.items.values() if i.get("kind") == "request"]}

    def put_item(self, Item: dict[str, Any]) -> None:  # noqa: N803
        self.items[Item["id"]] = dict(Item)

    def get_item(self, Key: dict[str, str], ConsistentRead: bool) -> dict[str, Any]:  # noqa: N803
        item = self.items.get(Key["id"])
        return {"Item": dict(item)} if item else {}


def test_dynamo_access_store() -> None:
    t = FakeTable()
    store = DynamoAccessStore(t)
    req = AccessRequestIn(email="r@example.com", reason="grading")
    store.submit(req, "c1")
    store.submit(req, "c1")
    [r] = store.list()
    assert r.status == "pending"
    assert t.items[r.id]["expires_at"] > 0
    with pytest.raises(RateLimited):
        for _ in range(PER_CLIENT_PER_HOUR):
            store.submit(AccessRequestIn(email="x@example.com", reason="grading"), "c1")
    assert store.decide(r.id, "approved", "owner@example.com") is not None
    assert store.decide(r.id, "rejected", "owner@example.com") is None
    assert store.get(r.id).status == "approved"  # type: ignore[union-attr]
    assert not any(k.startswith("rate#") for k in (x.id for x in store.list()))

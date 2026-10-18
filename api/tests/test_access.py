"""Demo access: public request form, admin-only approval, and the stores behind them."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from coachkg import auth
from coachkg.access import (
    MAX_PENDING,
    MODEL_CALLS_PER_DAY,
    MODEL_CALLS_PER_USER_PER_HOUR,
    PER_CLIENT_PER_HOUR,
    REQUEST_TTL,
    AccessRequest,
    AccessRequestIn,
    DemoUser,
    DynamoAccessStore,
    MemoryAccessStore,
    MemoryAccounts,
    ModelBudgetSpent,
    RateLimited,
    viewer_network,
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


@pytest.mark.parametrize(
    "bad",
    [
        {"email": "not-an-email"},
        {"reason": ""},
        {"reason": "x" * 501},
        {"name": "A\x00Reviewer"},
        {"reason": "Grading \u202etxt.exe"},
        {"email": "rev\u2066iewer@example.com"},
        {"email": "reviewer@example.com\x00"},
    ],
)
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


VIEWER = "X-Viewer-Ip"


@pytest.mark.parametrize(
    ("header", "key"),
    [
        ("203.0.113.9", "203.0.113.9"),
        ("2001:db8:1:2:aaaa:bbbb:cccc:dddd", "2001:db8:1:2::/64"),
        ("[2001:db8::1]", "2001:db8::/64"),
        ("203.0.113.9:51234", None),  # only the bare address the CloudFront function writes
        ("not-an-address", None),
        ("", None),
        (None, None),
    ],
)
def test_viewer_address_is_the_ip_or_the_ipv6_64(header: str | None, key: str | None) -> None:
    assert viewer_network(header) == key


def test_rate_limit_keys_on_the_cloudfront_viewer_address(cognito: TestClient, stores: Any) -> None:
    """X-Forwarded-For is the caller's to write; X-Viewer-Ip is written by CloudFront's function."""

    def post(i: int, viewer: str) -> int:
        headers = {VIEWER: viewer, "X-Forwarded-For": f"198.51.100.{i}"}
        r = cognito.post("/api/access-requests", json=REQ | {"email": f"v{i}@example.com"}, headers=headers)
        return r.status_code

    # Same IPv6 /64, different hosts and ports, a fresh X-Forwarded-For each time: one client.
    codes = [post(i, f"2001:db8:1:2::{i}") for i in range(PER_CLIENT_PER_HOUR + 1)]
    assert codes == [202] * PER_CLIENT_PER_HOUR + [429]
    assert post(50, "2001:db8:1:3::1") == 202
    assert post(51, "203.0.113.7") == 202


def test_pending_requests_are_capped() -> None:
    store = MemoryAccessStore()
    for i in range(MAX_PENDING):
        store.submit(AccessRequestIn(email=f"r{i}@example.com", reason="grading"), f"client{i}")
    with pytest.raises(RateLimited):
        store.submit(AccessRequestIn(email="late@example.com", reason="grading"), "client-late")
    # A full queue is refused before the per-client counter is touched.
    assert not any(k.startswith("client-late:") for k in store.hits)


def _expired(rid: str, email: str) -> AccessRequest:
    created = datetime.now(UTC) - REQUEST_TTL - timedelta(minutes=1)
    return AccessRequest(
        id=rid,
        email=email,
        name="",
        reason="old",
        status="pending",
        created_at=created.isoformat(timespec="seconds"),
    )


def test_expired_requests_are_gone_before_ttl_deletes_them() -> None:
    store = MemoryAccessStore()
    for i in range(MAX_PENDING):
        store.requests[f"old{i}"] = _expired(f"old{i}", f"old{i}@example.com")
    assert store.list() == [] and store.get("old0") is None
    assert store.decide("old0", "approved", "owner@example.com") is None
    # They don't count towards the cap, and the same email can ask again.
    store.submit(AccessRequestIn(email="old1@example.com", reason="grading"), "c1")
    assert [r.email for r in store.list()] == ["old1@example.com"]


def test_admin_rejects_every_pending_request(cognito: TestClient, stores: Any) -> None:
    access, accounts = stores
    for i in range(3):
        access.submit(AccessRequestIn(email=f"r{i}@example.com", reason="grading"), f"c{i}")
    access.decide(access.list()[0].id, "approved", "owner@example.com")
    assert cognito.post("/api/admin/requests/reject-pending", headers=_h()).status_code == 403
    r = cognito.post("/api/admin/requests/reject-pending", headers=_h(**ADMIN))
    assert r.status_code == 200 and r.json() == {"rejected": 2}
    assert sorted(x.status for x in access.list()) == ["approved", "rejected", "rejected"]
    assert accounts.users == {}


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
    for bad in ("jane.doe@gmail", "a\x00b@example.com"):
        r = cognito.post("/api/admin/users", json={"email": bad}, headers=_h(**ADMIN))
        assert r.status_code == 422
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
        self.scans = 0
        self.meta = type("M", (), {"client": type("C", (), {"exceptions": self._Exc})()})()

    def update_item(self, Key: dict[str, str], **kw: Any) -> dict[str, Any]:  # noqa: N803
        item = self.items.setdefault(Key["id"], {"id": Key["id"]})
        v = kw["ExpressionAttributeValues"]
        if kw["UpdateExpression"].startswith("ADD hits"):
            item["hits"] = item.get("hits", 0) + v[":one"]
            item["kind"] = v[":k"]
            return {"Attributes": {"hits": item["hits"]}}
        live = item.get("expires_at", 0) > v[":now"]
        if item.get("kind") != v[":k"] or item.get("status") != v[":p"] or not live:
            raise self._Exc.ConditionalCheckFailedException
        item.update(status=v[":s"], decided_by=v[":b"], decided_at=v[":a"])
        return {"Attributes": dict(item)}

    def scan(self, **kw: Any) -> dict[str, Any]:
        self.scans += 1
        now = kw["ExpressionAttributeValues"][":now"]
        items = self.items.values()
        return {"Items": [dict(i) for i in items if i.get("kind") == "request" and i["expires_at"] > now]}

    def query(self, **kw: Any) -> dict[str, Any]:
        assert kw["IndexName"] == "by-status"
        v = kw["ExpressionAttributeValues"]
        live = (i for i in self.items.values() if i.get("status") == v[":p"] and i["expires_at"] > v[":now"])
        return {"Items": [dict(i) for i in live]}

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
        for i in range(PER_CLIENT_PER_HOUR):
            store.submit(AccessRequestIn(email=f"x{i}@example.com", reason="grading"), "c1")
    assert store.decide(r.id, "approved", "owner@example.com") is not None
    assert store.decide(r.id, "rejected", "owner@example.com") is None
    assert store.get(r.id).status == "approved"  # type: ignore[union-attr]
    assert not any(k.startswith("rate#") for k in (x.id for x in store.list()))


def test_dynamo_store_never_scans_on_submit_and_ignores_expired() -> None:
    t = FakeTable()
    store = DynamoAccessStore(t)
    store.submit(AccessRequestIn(email="a@example.com", reason="grading"), "c1")
    store.submit(AccessRequestIn(email="b@example.com", reason="grading"), "c2")
    assert t.scans == 0
    [old] = [i for i in t.items.values() if i.get("email") == "a@example.com"]
    old["expires_at"] = int(time.time()) - 1
    assert [r.email for r in store.list()] == ["b@example.com"]
    assert store.get(old["id"]) is None
    assert store.decide(old["id"], "approved", "owner@example.com") is None
    assert store.reject_pending("owner@example.com") == 1
    assert old["status"] == "pending"  # expired: left for TTL and the purge job


def test_dynamo_full_queue_is_refused_before_the_counter() -> None:
    t = FakeTable()
    store = DynamoAccessStore(t)
    for i in range(MAX_PENDING):
        t.items[f"r{i}"] = {
            "id": f"r{i}",
            "kind": "request",
            "status": "pending",
            "email": f"r{i}@example.com",
            "expires_at": int(time.time()) + 3600,
        }
    with pytest.raises(RateLimited):
        store.submit(AccessRequestIn(email="late@example.com", reason="grading"), "c1")
    assert not any(k.startswith("rate#") for k in t.items)


def test_model_calls_are_capped_per_user_and_per_day() -> None:
    store = MemoryAccessStore()
    for _ in range(MODEL_CALLS_PER_USER_PER_HOUR):
        store.spend_model_call("user-a")
    with pytest.raises(ModelBudgetSpent):
        store.spend_model_call("user-a")
    store.spend_model_call("user-b")  # another reviewer has their own hourly budget
    for i in range(MODEL_CALLS_PER_DAY - MODEL_CALLS_PER_USER_PER_HOUR - 1):
        store.spend_model_call(f"user-{i % 50}-x")
    with pytest.raises(ModelBudgetSpent):
        store.spend_model_call("user-c")  # the whole demo's daily cap


def test_model_routes_answer_429_when_the_budget_is_spent(stores: Any) -> None:
    access, _ = stores
    for _ in range(MODEL_CALLS_PER_USER_PER_HOUR):
        access.spend_model_call("local")
    import dataclasses

    from coachkg.main import get_llm
    from coachkg.world import get_world

    # Model ids configured, so the routes get as far as the budget whatever the environment says.
    w = get_world()
    settings = dataclasses.replace(w.settings, llm_model_fast="fast-model", llm_model_main="main-model")
    app.dependency_overrides[get_world] = lambda: dataclasses.replace(w, settings=settings)
    # No API key in CI: the budget answers before any model call, so the client is never used.
    app.dependency_overrides[get_llm] = lambda: object()
    client = TestClient(app)
    r = client.post("/api/generate", json={"member_id": "mbr_01HX9JORDAN", "prompt": "upper body"})
    assert r.status_code == 429 and "budget" in r.json()["detail"]
    # The copilot and congratulation routes spend from the same budget.
    r = client.post("/api/members/mbr_01HX9JORDAN/copilot", json={"question": "hi"})
    assert r.status_code == 429
    assert client.post("/api/members/mbr_01HX9JORDAN/congratulate").status_code == 429

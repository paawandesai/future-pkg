"""Deployed auth: Cognito ID tokens only; mock auth never runs on Lambda; plan storage on DynamoDB."""

from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from coachkg import auth
from coachkg.main import app
from coachkg.plans import DynamoPlanStore

POOL = "us-east-1_TESTPOOL"
CLIENT = "testclient"
ISSUER = f"https://cognito-idp.us-east-1.amazonaws.com/{POOL}"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _id_jwt(key: Any = KEY, **over: Any) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": CLIENT,
        "token_use": "id",
        "iat": now,
        "exp": now + 600,
        "custom:coach_id": "coach_01HXSAM",
        **over,
    }
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, key, algorithm="RS256")


@pytest.fixture
def cognito(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTH_MODE", "cognito")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", POOL)
    monkeypatch.setenv("COGNITO_CLIENT_ID", CLIENT)
    monkeypatch.setattr(auth, "signing_key", lambda token, issuer: KEY.public_key())
    return TestClient(app)


def _members(client: TestClient, token: str | None) -> int:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.get("/api/members", headers=headers).status_code


def test_valid_id_token_scopes_to_its_coach(cognito: TestClient) -> None:
    r = cognito.get("/api/members", headers={"Authorization": f"Bearer {_id_jwt()}"})
    assert r.status_code == 200
    ids = [m["id"] for m in r.json()]
    assert "mbr_01HX9JORDAN" in ids and "mbr_01HXGEN0002" not in ids
    other = _id_jwt(**{"custom:coach_id": "coach_01HXOTHER"})
    r = cognito.get("/api/members", headers={"Authorization": f"Bearer {other}"})
    assert "mbr_01HX9JORDAN" not in [m["id"] for m in r.json()]


@pytest.mark.parametrize(
    "token",
    [
        None,
        _id_jwt(key=OTHER_KEY),
        _id_jwt(exp=int(time.time()) - 10),
        _id_jwt(aud="another-client"),
        _id_jwt(iss="https://cognito-idp.us-east-1.amazonaws.com/us-east-1_OTHER"),
        _id_jwt(token_use="access"),  # noqa: S106
        _id_jwt(**{"custom:coach_id": None}),
        jwt.encode(
            {"custom:coach_id": "coach_01HXSAM"}, "a-shared-secret-that-is-long-enough-x", algorithm="HS256"
        ),
    ],
    ids=[
        "none",
        "wrong-key",
        "expired",
        "wrong-audience",
        "wrong-issuer",
        "access-token",
        "no-coach",
        "hs256",
    ],
)
def test_bad_tokens_are_refused(cognito: TestClient, token: str | None) -> None:
    assert _members(cognito, token) == 401


def test_mock_auth_is_refused_on_lambda(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "mock")
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "future-pkg-api")
    assert _members(TestClient(app), None) == 401


def test_unknown_auth_mode_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "none")
    assert _members(TestClient(app), None) == 401


def test_responses_carry_noindex() -> None:
    assert TestClient(app).get("/healthz").headers["X-Robots-Tag"] == "noindex, nofollow"


class FakeTable:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    def put_item(self, Item: dict[str, Any], ConditionExpression: str) -> None:  # noqa: N803
        assert Item["id"] not in self.items
        self.items[Item["id"]] = dict(Item)

    def get_item(self, Key: dict[str, str], ConsistentRead: bool) -> dict[str, Any]:  # noqa: N803
        item = self.items.get(Key["id"])
        return {"Item": item} if item else {}

    def update_item(self, Key: dict[str, str], **kw: Any) -> None:  # noqa: N803
        item = self.items[Key["id"]]
        assert item["coach_id"] == kw["ExpressionAttributeValues"][":c"]
        item["status"] = kw["ExpressionAttributeValues"][":s"]
        item["body"] = kw["ExpressionAttributeValues"][":b"]


def test_dynamo_store_round_trip_with_ttl() -> None:
    table = FakeTable()
    store = DynamoPlanStore(table)
    plan = {"id": "p1", "coach_id": "c1", "member_id": "m1", "status": "draft", "created_at": "x", "w": 1.5}
    store.save(plan)
    assert table.items["p1"]["expires_at"] > time.time()
    assert store.get("p1") == plan
    assert store.confirm("p1", "someone-else") is None
    confirmed = store.confirm("p1", "c1")
    assert confirmed is not None and confirmed["status"] == "confirmed"
    assert store.get("p1")["status"] == "confirmed"  # type: ignore[index]
    assert store.get("missing") is None


def test_a_disabled_account_is_refused_within_a_minute() -> None:
    from coachkg import auth as a

    calls: list[str] = []

    def lookup(pool: str, user: str) -> bool:
        calls.append(user)
        return user != "disabled-user"

    a._enabled.clear()
    assert a.user_enabled("us-east-1_x", "reviewer", lookup)
    assert a.user_enabled("us-east-1_x", "reviewer", lookup)  # cached
    assert calls == ["reviewer"]
    assert not a.user_enabled("us-east-1_x", "disabled-user", lookup)
    assert not a.user_enabled("us-east-1_x", "", lookup)


def test_a_failed_lookup_fails_closed() -> None:
    from coachkg import auth as a

    def broken(pool: str, user: str) -> bool:
        raise RuntimeError("cognito unavailable")

    a._enabled.clear()
    assert not a.user_enabled("us-east-1_x", "someone", broken)

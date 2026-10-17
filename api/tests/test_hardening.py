"""Deployment hardening: CloudFront-only access, no slash redirects, no caching, errors that log
nothing a user or a model wrote, and Cognito as the default auth mode."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from coachkg import config, main
from coachkg.llm import LLM, LLMError
from coachkg.main import app, get_llm
from coachkg.plans import DynamoPlanStore
from coachkg.world import get_world
from tests.test_auth import FakeTable as PlanTable

SECRET = "generated-origin-value"  # noqa: S105 - a test value, not a credential


@pytest.fixture
def origin(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ORIGIN_SECRET_ID", "test/origin")
    monkeypatch.setattr(config, "_secret_value", lambda secret_id: SECRET)
    return TestClient(app)


@pytest.fixture
def records() -> Iterator[list[logging.LogRecord]]:
    out: list[logging.LogRecord] = []

    class Keep(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            out.append(record)

    h = Keep()
    main.access_log.addHandler(h)
    yield out
    main.access_log.removeHandler(h)


def test_requests_without_the_cloudfront_header_are_refused(origin: TestClient) -> None:
    assert origin.get("/api/members").status_code == 403
    assert origin.get("/api/members", headers={"X-Origin-Verify": "guess"}).status_code == 403
    assert origin.post("/api/access-requests", json={}).status_code == 403
    assert origin.get("/api/members", headers={"X-Origin-Verify": SECRET}).status_code == 200
    # The Lambda Web Adapter's readiness check comes from localhost without the header.
    assert origin.get("/healthz").status_code == 200


def test_origin_check_fails_closed_when_the_secret_cant_be_read(
    monkeypatch: pytest.MonkeyPatch, records: list[logging.LogRecord]
) -> None:
    def boom(secret_id: str) -> str:
        raise RuntimeError("AccessDenied for arn:aws:secretsmanager:...")

    monkeypatch.setenv("ORIGIN_SECRET_ID", "test/origin")
    monkeypatch.setattr(config, "_secret_value", boom)
    assert TestClient(app).get("/api/members", headers={"X-Origin-Verify": SECRET}).status_code == 503
    assert all("arn:" not in r.getMessage() for r in records)


def test_no_header_needed_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORIGIN_SECRET_ID", raising=False)
    assert TestClient(app).get("/api/members").status_code == 200


def test_trailing_slash_is_not_redirected() -> None:
    r = TestClient(app).get("/api/me/", follow_redirects=False)
    assert r.status_code == 404 and "location" not in r.headers


def test_api_responses_are_not_stored() -> None:
    c = TestClient(app)
    for path in ("/api/members", "/api/me", "/healthz", "/api/nope"):
        assert c.get(path).headers["Cache-Control"] == "no-store"


def test_unhandled_errors_log_the_class_and_route_only(records: list[logging.LogRecord]) -> None:
    def broken() -> Any:
        raise RuntimeError("member said: my knee is sore")

    app.dependency_overrides[get_world] = broken
    try:
        r = TestClient(app, raise_server_exceptions=False).get("/api/members/mbr_01HX9JORDAN")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 500 and "knee" not in r.text
    logged = " ".join(rec.getMessage() for rec in records)
    assert "RuntimeError" in logged and "/api/members/{member_id}" in logged
    assert "knee" not in logged and "mbr_01HX9JORDAN" not in logged


def test_errors_inside_the_plan_stream_end_it_cleanly(
    monkeypatch: pytest.MonkeyPatch, records: list[logging.LogRecord]
) -> None:
    async def run(*args: Any) -> AsyncIterator[dict[str, Any]]:
        yield {"event": "stage", "stage": "intent"}
        raise ValueError("model wrote: left knee")

    monkeypatch.setattr(main, "run", run)
    app.dependency_overrides[get_llm] = lambda: object()
    try:
        r = TestClient(app).post("/api/generate", json={"member_id": "mbr_01HX9JORDAN", "prompt": "upper"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.text.rstrip().endswith('"message": "Something went wrong. Try again."}')
    assert "knee" not in r.text
    assert all("knee" not in rec.getMessage() for rec in records)


def test_auth_defaults_to_cognito(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTH_MODE")
    monkeypatch.delenv("COGNITO_USER_POOL_ID", raising=False)
    assert config.load_settings().auth_mode == "cognito"
    c = TestClient(app)
    assert c.get("/api/members").status_code == 401
    assert c.get("/api/admin/requests").status_code == 401


class Out(BaseModel):
    region: str


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_unparseable_model_output_is_an_llm_error_without_its_text(stop_reason: str) -> None:
    """The SDK validates before stop_reason is visible; the error must still fail closed and must
    not carry the model's words."""

    def handler(request: httpx2.Request) -> httpx2.Response:
        body = {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "m",
            "content": [{"type": "text", "text": "I can't help with the left knee"}],
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        return httpx2.Response(200, json=body)

    http = httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
    client = anthropic.AsyncAnthropic(api_key="test-not-a-key", http_client=http)
    llm = LLM(client=client)
    llm.fallback_models = frozenset()
    with pytest.raises(LLMError) as err:
        asyncio.run(llm.parse(purpose="intent", model="m", system="s", user="u", schema=Out))
    assert "knee" not in str(err.value) and err.value.__cause__ is None


def test_expired_plans_are_gone_before_ttl_deletes_them() -> None:
    table = PlanTable()
    store = DynamoPlanStore(table)
    store.save({"id": "p1", "coach_id": "c1", "member_id": "m1", "status": "draft", "created_at": "x"})
    table.items["p1"]["expires_at"] = int(time.time()) - 1
    assert store.get("p1") is None
    assert store.confirm("p1", "c1") is None

from fastapi.testclient import TestClient

from coachkg import health
from coachkg.main import app


def test_healthz_reports_configuration_and_last_successes_only() -> None:
    r = TestClient(app).get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["auth_mode"] == "mock"
    assert set(body) == {
        "status",
        "auth_mode",
        "models_configured",
        "started_at",
        "last_model_call_ok_at",
        "last_plan_saved_at",
    }
    # No model ids, keys or secrets.
    assert "claude" not in r.text.lower() and "key" not in r.text.lower()


def test_healthz_shows_the_last_success() -> None:
    health.mark("last_plan_saved_at")
    assert TestClient(app).get("/healthz").json()["last_plan_saved_at"] is not None

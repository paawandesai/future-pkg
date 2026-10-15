"""Generator pipeline (plan assembly, selection validation, confirm). The model is a test double
here; the live path is covered by scripts/measure_latency.py and the eval scenarios."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from coachkg.config import load_settings
from coachkg.generator.assemble import BLOCKS
from coachkg.generator.intent import Intent
from coachkg.generator.pipeline import GenerateRequest, run
from coachkg.generator.selection import Selection, validate
from coachkg.llm import CallStats
from coachkg.main import app, get_llm, get_plans
from coachkg.plans import SqlitePlanStore
from coachkg.world import World, build_world, get_world


class FakeLLM:
    """Returns a fixed intent and a selection built by `pick` from the offered ids."""

    def __init__(self, intent: Intent, pick: Callable[[list[str]], Selection]) -> None:
        self.intent = intent
        self.pick = pick
        self.seen_users: list[str] = []

    async def parse(self, *, purpose: str, model: str, user: str, **_: Any) -> tuple[Any, CallStats]:
        self.seen_users.append(user)
        stats = CallStats(purpose, model, model, 1, 0, 0)
        if purpose == "intent":
            return self.intent, stats
        offered = re.findall(r'"id": "(E\d+)"', user)
        return self.pick(offered), stats


def _intent(**kw: Any) -> Intent:
    base: dict[str, Any] = {
        "focus": None,
        "exclusions": None,
        "injury_mentions": None,
        "unavailable_equipment": None,
        "minutes": None,
    }
    return Intent(**{**base, **kw})


def _all_offered(ids: list[str]) -> Selection:
    # Puts every offered id in every block, plus ids that were never offered.
    return Selection(warmup=ids + ["E999"], main=ids + ["E0", "nope"], cooldown=ids)


@pytest.fixture(scope="module")
def world(data_dir: Path, monkeypatch_module: pytest.MonkeyPatch) -> World:
    monkeypatch_module.setenv("LLM_MODEL_FAST", "fast-model")
    monkeypatch_module.setenv("LLM_MODEL_MAIN", "main-model")
    return build_world(load_settings())


@pytest.fixture(scope="module")
def monkeypatch_module() -> Any:
    mp = pytest.MonkeyPatch()
    yield mp
    mp.undo()


def _run(world: World, llm: FakeLLM, prompt: str, **kw: Any) -> list[dict[str, Any]]:
    member = next(iter(world.members.values()))
    req = GenerateRequest(member_id=member.id, prompt=prompt, **kw)

    async def collect() -> list[dict[str, Any]]:
        return [e async for e in run(world, llm, req, member, "coach_01HXSAM")]  # type: ignore[arg-type]

    return asyncio.run(collect())


def _plan(events: list[dict[str, Any]]) -> dict[str, Any]:
    plan: dict[str, Any] | None = next((e["plan"] for e in events if e["event"] == "plan"), None)
    assert plan is not None, events
    return plan


def _ids(plan: dict[str, Any]) -> list[str]:
    return [i["exercise_id"] for b in plan["blocks"] for i in b["items"]]


@pytest.mark.parametrize("minutes", [15, 30, 45, 60])
def test_time_budget_is_respected(world: World, minutes: int) -> None:
    plan = _plan(_run(world, FakeLLM(_intent(), _all_offered), "upper body", minutes=minutes))
    assert plan["minutes_planned"] <= minutes
    for b in plan["blocks"]:
        assert b["minutes"] <= b["budget_minutes"] + 0.05


def test_ids_outside_the_safe_set_are_dropped(world: World) -> None:
    events = _run(world, FakeLLM(_intent(injury_mentions=["left knee"]), _all_offered), "knee sore")
    plan = _plan(events)
    member = next(iter(world.members.values()))
    from coachkg.safety import SafetyRequest

    safe = {e.id for e in world.safety.run(SafetyRequest(member=member)).candidates}
    assert set(_ids(plan)) <= safe
    assert len(_ids(plan)) == len(set(_ids(plan)))
    assert any("not on the safe list" in n for n in plan["trace"]["notes"])


def test_validate_keeps_order_and_drops_cross_block_ids() -> None:
    from coachkg.data import Exercise

    def ex(i: str) -> Exercise:
        return Exercise(
            id=i,
            name=i,
            muscle_groups=[],
            joints_loaded=[],
            movement_patterns=[],
            equipment_required=[],
            is_bilateral=True,
            side=None,
        )

    ids = {"E1": ("warmup", ex("a")), "E2": ("main", ex("b")), "E3": ("main", ex("c"))}
    sel = validate(Selection(warmup=["E2", "E1"], main=["E3", "E2", "E3"], cooldown=["E1"]), ids, None)  # type: ignore[arg-type]
    assert [e.id for e in sel.chosen["main"]] == ["c", "b"]
    assert [e.id for e in sel.chosen["warmup"]] == ["a"]
    assert sel.chosen["cooldown"] == []
    assert sorted(sel.dropped) == ["E1", "E2", "E3"]


def test_injury_missed_by_the_model_is_still_caught(world: World) -> None:
    """The deterministic scan runs even when intent extraction returns no injury."""
    plan = _plan(_run(world, FakeLLM(_intent(), _all_offered), "Upper body, her shoulder is sore"))
    regions = {r for row in plan["trace"]["restrictions"] for r in row["regions"]}
    assert "region:shoulder" in regions


def test_unresolvable_injury_blocks_drafting(world: World) -> None:
    events = _run(world, FakeLLM(_intent(injury_mentions=["her thingy"]), _all_offered), "her thingy hurts")
    assert events[-1]["event"] == "blocked"
    assert not any(e["event"] == "plan" for e in events)


def test_member_chat_text_never_reaches_the_selection_prompt(world: World) -> None:
    llm = FakeLLM(_intent(), _all_offered)
    _plan(_run(world, llm, "upper body"))
    member = next(iter(world.members.values()))
    selection_prompt = llm.seen_users[-1]
    for msg in member.chat_history:
        if len(msg.text) > 20:
            assert msg.text not in selection_prompt


def test_missing_equipment_word_removes_every_match(world: World) -> None:
    plan = _plan(_run(world, FakeLLM(_intent(unavailable_equipment=["bench"]), _all_offered), "no bench"))
    for b in plan["blocks"]:
        for i in b["items"]:
            assert not any("Bench" in q for q in i["equipment"]), i["name"]


def test_plan_is_a_draft_and_unsigned_programming_is_disclosed(world: World) -> None:
    plan = _plan(_run(world, FakeLLM(_intent(), _all_offered), "upper body"))
    assert plan["status"] == "draft"
    assert "Coach decision support" in plan["label"]
    assert any("programming.yaml" in line for line in plan["trace"]["unverified"])


def test_api_scopes_members_and_confirms_plans(world: World, tmp_path: Path) -> None:
    store = SqlitePlanStore(tmp_path / "plans.sqlite3")
    app.dependency_overrides[get_plans] = lambda: store
    app.dependency_overrides[get_llm] = lambda: FakeLLM(_intent(), _all_offered)
    app.dependency_overrides[get_world] = lambda: world
    try:
        client = TestClient(app)
        assert client.post("/api/generate", json={"member_id": "mbr_other", "prompt": "x"}).status_code == 404
        member_id = client.get("/api/members").json()[0]["id"]
        resp = client.post("/api/generate", json={"member_id": member_id, "prompt": "upper body"})
        assert resp.status_code == 200
        plan_events = [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith("data: ")]
        plan = next(e["plan"] for e in plan_events if e["event"] == "plan")
        assert client.get(f"/api/plans/{plan['id']}").json()["status"] == "draft"
        confirmed = client.post(f"/api/plans/{plan['id']}/confirm").json()
        assert confirmed["status"] == "confirmed"
        assert client.get(f"/api/plans/{plan['id']}").json()["confirmed_by"] == "coach_01HXSAM"
    finally:
        app.dependency_overrides.clear()


def test_blocks_are_ordered(world: World) -> None:
    plan = _plan(_run(world, FakeLLM(_intent(), _all_offered), "upper body"))
    assert [b["name"] for b in plan["blocks"]] == list(BLOCKS)

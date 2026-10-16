"""Generator pipeline (plan assembly, selection validation, confirm). The model is a test double
here; the live path is covered by scripts/measure_latency.py and the eval scenarios."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from coachkg.config import load_settings
from coachkg.generator.assemble import BLOCKS
from coachkg.generator.intent import Intent
from coachkg.generator.pipeline import GenerateRequest, run
from coachkg.generator.selection import Selection, validate
from coachkg.kg.rules import Review
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


def _run(world: World, llm: FakeLLM, prompt: str, who: str | None = None, **kw: Any) -> list[dict[str, Any]]:
    members = list(world.members.values())
    member = next(m for m in members if m.name == who) if who else members[0]
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
    # Signed in memory: the plan doesn't flag it.
    disk = world.programming
    signed_review = Review(status="signed", reviewer="TEST", signed_on=date(2026, 10, 16))
    world.programming = disk.model_copy(update={"review": signed_review})
    try:
        signed = _plan(_run(world, FakeLLM(_intent(), _all_offered), "upper body"))
    finally:
        world.programming = disk
    assert not any("programming.yaml" in line for line in signed["trace"]["unverified"])

    # Draft in memory: the plan must disclose the model-drafted defaults.
    world.programming = disk.model_copy(update={"review": Review()})
    try:
        plan = _plan(_run(world, FakeLLM(_intent(), _all_offered), "upper body"))
    finally:
        world.programming = disk
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


def _run_for(world: World, member_id: str, llm: FakeLLM, prompt: str, **kw: Any) -> dict[str, Any]:
    member = world.members[member_id]
    req = GenerateRequest(member_id=member_id, prompt=prompt, **kw)

    async def collect() -> list[dict[str, Any]]:
        return [e async for e in run(world, llm, req, member, "coach_01HXSAM")]  # type: ignore[arg-type]

    return _plan(asyncio.run(collect()))


def test_missing_equipment_surfaces_equivalent_alternatives(world: World) -> None:
    llm = FakeLLM(_intent(focus=["upper body"], unavailable_equipment=["Barbell"]), _all_offered)
    plan = _run_for(world, "mbr_01HXGEN0002", llm, "upper body, no barbell today", minutes=30)
    alts = plan["trace"]["alternatives"]
    assert alts, "expected alternatives for barbell exercises"
    from coachkg.safety import SafetyRequest

    member = world.members["mbr_01HXGEN0002"]
    safe = {e.id for e in world.safety.run(SafetyRequest(member=member)).candidates}
    first = alts[0]
    assert "Barbell" in first["needs"]
    assert first["use_id"] in safe
    assert first["shared_patterns"] and first["shared_muscles"]
    kinds = {e["kind"] for e in first["path"]}
    assert {"has-pattern", "targets"} <= kinds


def test_signed_substitute_edge_ranks_first(world: World) -> None:
    llm = FakeLLM(_intent(focus=["lower body"], unavailable_equipment=["Kettlebell"]), _all_offered)
    plan = _run_for(world, "mbr_01HXGEN0006", llm, "lower body, no kettlebell", minutes=30)
    subs = [a for a in plan["trace"]["alternatives"] if a["substitute"]]
    assert subs and subs[0]["substitute"] == {
        "use": "Dumbbell",
        "for": "Kettlebell",
        "source": "kg/rules/equipment.yaml",
    }
    assert subs[0]["path"][-1]["kind"] == "substitutes-for"


def test_disliked_exercises_are_left_out_unless_requested(world: World) -> None:
    llm = FakeLLM(_intent(focus=["cardio"]), _all_offered)
    plan = _run_for(world, "mbr_01HXGEN0004", llm, "cardio", minutes=30)
    assert "Jumping Jack" not in {i["name"] for b in plan["blocks"] for i in b["items"]}
    assert any("dislike" in n and "Jumping Jack" in n for n in plan["trace"]["notes"])


def test_items_split_reasons_and_carry_graph_path(world: World) -> None:
    plan = _plan(_run(world, FakeLLM(_intent(focus=["upper body"]), _all_offered), "upper body"))
    items = [i for b in plan["blocks"] for i in b["items"]]
    focused = [i for i in items if "matches the requested focus" in i["why"]]
    assert focused
    for i in focused:
        assert i["path"] and all(e["src"] == f"ex:{i['exercise_id']}" for e in i["path"])
    for i in items:
        assert not any(w.startswith("member dislikes") for w in i["why"])
        assert all(isinstance(r, str) for r in i["counted_against"])


def test_time_field_wins_over_prompt_and_conflict_is_noted(world: World) -> None:
    plan = _plan(_run(world, FakeLLM(_intent(minutes=20), _all_offered), "20 min upper body", minutes=45))
    assert plan["minutes_requested"] == 45
    assert any("mentions 20 minutes" in n for n in plan["trace"]["notes"])


def test_falling_adherence_gives_a_lighter_main_block(world: World) -> None:
    from datetime import date

    from coachkg.generator.programming import journey_reason

    prog = world.programming
    assert journey_reason(prog, "2020-01-01", [100, 100, 75, 50], date(2026, 6, 8))
    assert journey_reason(prog, "2020-01-01", [80, 85, 80, 75], date(2026, 6, 8)) is None
    assert "joined 10 days ago" in (journey_reason(prog, "2026-05-29", [], date(2026, 6, 8)) or "")

    jordan = next(iter(world.members.values()))
    weekly = [w["pct"] for w in (jordan.adherence or {})["weekly_completion_pct"]]
    assert weekly[0] - weekly[-1] >= 25  # Jordan's data: 100 -> 50

    plan = _plan(_run(world, FakeLLM(_intent(), _all_offered), "upper body", minutes=20))
    main = next(b for b in plan["blocks"] if b["name"] == "main")
    assert main["items"] and all(i["sets"] <= 2 for i in main["items"])
    assert any(n.startswith("Lighter main block") for n in plan["trace"]["notes"])


def test_journey_rule_never_leaves_the_time_window_half_empty(world: World) -> None:
    # Jordan's knee restriction leaves too few safe exercises to fill 45 minutes at 2 sets.
    plan = _plan(_run(world, FakeLLM(_intent(), _all_offered), "upper body", minutes=45))
    notes = plan["trace"]["notes"]
    lighter = any(n.startswith("Lighter main block") for n in notes)
    kept = any("Kept the default sets" in n for n in notes)
    assert lighter != kept
    if kept:
        main = next(b for b in plan["blocks"] if b["name"] == "main")
        assert any(i["sets"] == 3 for i in main["items"])


def test_steady_member_keeps_default_sets(world: World) -> None:
    llm = FakeLLM(_intent(focus=["upper body"]), _all_offered)
    plan = _run_for(world, "mbr_01HXGEN0002", llm, "upper body", minutes=45)
    assert not any(n.startswith("Lighter main block") for n in plan["trace"]["notes"])


# ---------- the brief's own example requests ----------


def _names(world: World, plan: dict[str, Any]) -> set[str]:
    by_id = {e.id: e.name for e in world.catalog} | {e.id: e.name for e in world.rules.authored}
    return {by_id[i] for i in _ids(plan)}


def test_brief_knee_example_keeps_lower_body_work(world: World) -> None:
    prompt = "lower-body exercises that avoid aggravating a knee injury"
    it = _intent(focus=["lower-body exercises"], injury_mentions=["knee"])
    plan = _plan(_run(world, FakeLLM(it, _all_offered), prompt, who="Elena Petrova"))
    assert [r["regions"] for r in plan["trace"]["restrictions"]] == [["region:knee"]]
    names = _names(world, plan)
    assert names & {"Dumbbell Romanian Deadlift", "Kettlebell Romanian Deadlift", "Glute Bridge"}, names


def test_brief_deadlift_variations_are_excluded(world: World) -> None:
    it = _intent(exclusions=["deadlift variations"])
    plan = _plan(_run(world, FakeLLM(it, _all_offered), "Exclude deadlifts", who="Elena Petrova"))
    assert not any("Deadlift" in n for n in _names(world, plan))


def test_unmatched_exclusion_fails_closed(world: World) -> None:
    it = _intent(exclusions=["zorbing"])
    events = _run(world, FakeLLM(it, _all_offered), "no zorbing", who="Elena Petrova")
    assert not any(e["event"] == "plan" for e in events)
    assert any(e["event"] == "error" and "zorbing" in e["message"] for e in events)


def test_only_named_equipment_is_used(world: World) -> None:
    it = _intent(unavailable_equipment=["barbell"], available_only=["dumbbells", "kettlebell"])
    prompt = "She has no barbell, only dumbbells and a kettlebell"
    plan = _plan(_run(world, FakeLLM(it, _all_offered), prompt, who="Sam Okafor"))
    needs = {q for e in world.catalog if e.id in _ids(plan) for q in e.equipment_required}
    assert needs <= {"Dumbbell", "Kettlebell"}, needs


def test_shorthand_focus_resolves(world: World) -> None:
    it = _intent(focus=["full-body", "isolation around my pecs"])
    plan = _plan(_run(world, FakeLLM(it, _all_offered), "full-body exercise with isolation around my pecs"))
    understood = {str(row.get("understood_as")).lower() for row in plan["trace"]["read"]}
    assert "chest" in understood, plan["trace"]["read"]


def test_a_rejected_key_says_so(world: World) -> None:
    from coachkg.llm import LLMAuthError

    class NoKey(FakeLLM):
        async def parse(self, **_: Any) -> tuple[Any, CallStats]:
            raise LLMAuthError("intent: AuthenticationError")

    events = _run(world, NoKey(_intent(), _all_offered), "upper body")
    assert any(e["event"] == "error" and "API key" in e["message"] for e in events)

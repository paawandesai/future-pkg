"""Copilot data, churn, charts and scoping. The model is a test double here."""

from __future__ import annotations

import asyncio
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from coachkg.config import load_settings
from coachkg.copilot import agent, data
from coachkg.main import app, get_llm
from coachkg.world import World, build_world


@pytest.fixture(scope="module")
def world(data_dir: Any) -> World:
    return build_world(load_settings())


@pytest.fixture(scope="module")
def ctx(world: World) -> data.MemberContext:
    return world.context(world.members["mbr_01HX9JORDAN"])


def test_churn_is_deterministic_and_ignores_labs(world: World, ctx: data.MemberContext) -> None:
    c = data.churn(ctx)
    assert c.score == sum(f.points for f in c.features)
    assert c.level == "elevated"
    names = " ".join(f.name.lower() for f in c.features)
    assert "lab" not in names and "dexa" not in names and "sleep" not in names
    # Changing labs and biomarkers does not move the score.
    other = ctx.member.model_copy(update={"labs": {}, "biomarkers": {}})
    assert data.churn(data.MemberContext(other, ctx.logins, ctx.as_of, [])).score == c.score
    assert c.brief_text == ctx.member.coach_brief["churn_risk"]  # type: ignore[index]


def test_chart_rejects_unknown_metrics_and_takes_no_values(ctx: data.MemberContext) -> None:
    with pytest.raises(ValueError):
        data.make_chart(ctx, ["ldl_mg_dl"])
    with pytest.raises(ValueError):
        data.make_chart(ctx, ["sleep_hours", "logins"])
    spec = data.make_chart(ctx, ["logins", "member_messages"], "bar", 4)
    assert len(spec.data) == 4
    assert any("generated" in n for n in spec.notes)


def test_quick_charts_need_no_model(ctx: data.MemberContext) -> None:
    for build in data.QUICK_CHARTS.values():
        assert build(ctx).data


def test_labs_are_values_only(ctx: data.MemberContext) -> None:
    out = data.get_labs(ctx)
    assert out["labs"] == ctx.member.labs
    assert set(out) == {"labs", "note"}


def test_chat_is_quoted_with_provenance_and_no_images(ctx: data.MemberContext) -> None:
    msgs = data.get_chat(ctx)["messages"]
    assert {m["provenance"] for m in msgs} == {"member-said", "coach-said"}
    for m in msgs:
        for a in m["attachments"]:
            assert set(a) == {"type", "caption"}


def test_changes_since(ctx: data.MemberContext) -> None:
    ch = data.get_changes(ctx, date(2026, 6, 1))
    assert {s["date"] for s in ch["sessions"]} == {"2026-06-01", "2026-06-03"}


def test_no_tool_can_write_send_or_pick_a_member() -> None:
    names = {t["name"] for t in agent.TOOLS}
    assert not {n for n in names if any(w in n for w in ("send", "write", "update", "delete", "set_"))}
    for t in agent.TOOLS:
        assert "member" not in " ".join(t["input_schema"]["properties"]).lower()


class ToolThenAnswer:
    """First turn asks for get_chat and make_chart; second turn answers."""

    def __init__(self) -> None:
        self.calls: list[list[Any]] = []

    async def create(self, *, messages: list[Any], **_: Any) -> tuple[Any, int]:
        self.calls.append(list(messages))
        if len(self.calls) == 1:
            content = [
                SimpleNamespace(type="tool_use", id="t1", name="get_chat", input={"since": None}),
                SimpleNamespace(
                    type="tool_use",
                    id="t2",
                    name="make_chart",
                    input={"metrics": ["ldl"], "chart_type": "line", "weeks": 4},
                ),
            ]
            return SimpleNamespace(stop_reason="tool_use", content=content), 1
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="ok")]), 1


def test_loop_runs_tools_on_the_member_on_screen(ctx: data.MemberContext) -> None:
    llm = ToolThenAnswer()
    ans = asyncio.run(agent.ask(llm, "m", ctx, "what did she say?"))  # type: ignore[arg-type]
    assert ans.text == "ok" and ans.tools_used == ["get_chat", "make_chart"]
    results = llm.calls[1][-1]["content"]
    assert ctx.member.chat_history[0].text[:20] in results[0]["content"]
    assert results[1]["is_error"] is True  # invalid metric is refused, not drawn
    assert ans.charts == []


def test_api_scopes_copilot_to_the_coachs_members(world: World) -> None:
    app.dependency_overrides[get_llm] = lambda: ToolThenAnswer()
    try:
        client = TestClient(app)
        assert client.get("/api/members/mbr_01HXGEN0002").status_code == 404
        assert client.post("/api/members/mbr_01HXGEN0002/copilot", json={"question": "hi"}).status_code == 404
        assert client.get("/api/members/mbr_01HXGEN0002/charts/sleep").status_code == 404
        view = client.get("/api/members/mbr_01HX9JORDAN").json()
        assert view["fictional"] and view["as_of"] == "2026-06-04"
        assert "login events" in view["generated_inputs"]
    finally:
        app.dependency_overrides.clear()


def test_member_graph_keeps_chat_provenance(world: World) -> None:
    g = world.member_graphs["mbr_01HX9JORDAN"]
    mentions = [e for e in g.all_edges() if e.kind == "mentions"]
    assert mentions and all(e.prov in ("member-said", "coach-said") for e in mentions)

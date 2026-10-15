"""HTTP API. Request and response bodies are never logged."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from coachkg.auth import current_coach
from coachkg.config import REPO_ROOT
from coachkg.copilot import agent, data
from coachkg.generator.pipeline import GenerateRequest, run
from coachkg.llm import LLM, LLMError
from coachkg.member import Member
from coachkg.plans import PlanStore, SqlitePlanStore
from coachkg.world import World, get_world

app = FastAPI(title="coachkg", docs_url=None, redoc_url=None, openapi_url=None)

Coach = Annotated[str, Depends(current_coach)]


@lru_cache(maxsize=1)
def get_plans() -> PlanStore:
    return SqlitePlanStore(Path(os.environ.get("PLAN_DB", REPO_ROOT / ".cache" / "plans.sqlite3")))


@lru_cache(maxsize=1)
def get_llm() -> LLM:
    return LLM()


WorldDep = Annotated[World, Depends(get_world)]
PlansDep = Annotated[PlanStore, Depends(get_plans)]
LLMDep = Annotated[LLM, Depends(get_llm)]


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Configuration-level health only: never calls a model or reads a secret."""
    return {"status": "ok"}


@app.get("/api/members")
def list_members(coach: Coach, world: WorldDep) -> list[dict[str, Any]]:
    return [
        {"id": m.id, "name": m.name, "fictional": True}
        for m in world.members.values()
        if m.profile.get("coach_id") == coach
    ]


def _sse(event: dict[str, Any]) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.post("/api/generate")
async def generate(
    req: GenerateRequest, coach: Coach, world: WorldDep, plans: PlansDep, llm: LLMDep
) -> StreamingResponse:
    member = world.member_for_coach(req.member_id, coach)
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    async def stream() -> AsyncIterator[str]:
        async for event in run(world, llm, req, member, coach):
            if event["event"] == "plan":
                plans.save(event["plan"])
            yield _sse(event)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})


@app.get("/api/plans/{plan_id}")
def get_plan(plan_id: str, coach: Coach, plans: PlansDep) -> dict[str, Any]:
    plan = plans.get(plan_id)
    if plan is None or plan["coach_id"] != coach:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@app.post("/api/plans/{plan_id}/confirm")
def confirm_plan(plan_id: str, coach: Coach, plans: PlansDep) -> dict[str, Any]:
    plan = plans.confirm(plan_id, coach)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"id": plan["id"], "status": plan["status"], "confirmed_at": plan["confirmed_at"]}


# ---------- member view and copilot (surface B) ----------


def _member(member_id: str, coach: str, world: World) -> Member:
    m = world.member_for_coach(member_id, coach)
    if m is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return m


@app.get("/api/members/{member_id}")
def member_view(member_id: str, coach: Coach, world: WorldDep) -> dict[str, Any]:
    m = _member(member_id, coach, world)
    ctx = world.context(m)
    return {
        "id": m.id,
        "name": m.name,
        "fictional": True,
        "as_of": world.settings.as_of_date.isoformat(),
        "generated_inputs": ctx.generated_inputs,
        "profile": {k: m.profile.get(k) for k in ("age", "sex", "timezone", "member_since", "tier")},
        "goals": m.goals,
        "preferences": m.preferences,
        "equipment_available": m.equipment_available,
        "injuries": [i.model_dump() | {"active": i.active} for i in m.injuries],
        "history": m.workout_history,
        "brief": data.get_brief(ctx),
        "adherence": data.get_adherence(ctx),
        "sleep": data.get_sleep(ctx),
        "labs": data.get_labs(ctx),
        "chat": data.get_chat(ctx)["messages"],
        "churn": data.churn(ctx).model_dump(),
        "review_mentions": _review_mentions(m, world),
    }


def _review_mentions(m: Member, world: World) -> list[dict[str, Any]]:
    """Member messages that mention a body region with an active injury. Shown to the coach as
    something to review; they never change the restriction."""
    g = world.member_graphs[m.id]
    injured = {e.dst for i in m.injuries if i.active for e in g.out_edges(f"injury:{i.id}", "located-at")}
    out = []
    for e in g.all_edges():
        if e.kind == "mentions" and e.prov == "member-said" and e.dst in injured:
            msg = m.chat_history[int(e.src.split(":", 1)[1])]
            out.append({"ts": msg.ts, "quote": msg.text, "region": g.node(e.dst).get("label")})
    return out


@app.get("/api/members/{member_id}/charts/{kind}")
def quick_chart(member_id: str, kind: str, coach: Coach, world: WorldDep) -> dict[str, Any]:
    """Quick-prompt charts: deterministic, no model call."""
    m = _member(member_id, coach, world)
    if kind not in data.QUICK_CHARTS:
        raise HTTPException(status_code=404, detail="Unknown chart")
    return data.QUICK_CHARTS[kind](world.context(m)).model_dump()


class CopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@app.post("/api/members/{member_id}/copilot")
async def copilot(
    member_id: str, req: CopilotRequest, coach: Coach, world: WorldDep, llm: LLMDep
) -> dict[str, Any]:
    m = _member(member_id, coach, world)
    model = world.settings.llm_model_main
    if not model:
        raise HTTPException(status_code=503, detail="Model ids are not configured")
    try:
        ans = await agent.ask(llm, model, world.context(m), req.question)
    except LLMError:
        raise HTTPException(status_code=502, detail="The copilot couldn't answer. Try again.") from None
    return {
        "answer": ans.text,
        "charts": [c.model_dump() for c in ans.charts],
        "tools_used": ans.tools_used,
        "disclosure": ans.disclosure,
        "model_ms": ans.model_ms,
    }


@app.post("/api/members/{member_id}/congratulate")
async def congratulate(member_id: str, coach: Coach, world: WorldDep, llm: LLMDep) -> dict[str, Any]:
    """A draft for the coach. There is no endpoint or tool that sends it."""
    m = _member(member_id, coach, world)
    model = world.settings.llm_model_main
    if not model:
        raise HTTPException(status_code=503, detail="Model ids are not configured")
    try:
        return await agent.congratulation_draft(llm, model, world.context(m))
    except LLMError:
        raise HTTPException(status_code=502, detail="Couldn't draft the message. Try again.") from None


@app.get("/api/members/{member_id}/graph")
def member_graph(member_id: str, coach: Coach, world: WorldDep) -> dict[str, Any]:
    m = _member(member_id, coach, world)
    g = world.member_graphs[m.id]
    return {
        "nodes": [{"id": n, "kind": d.get("kind"), "label": d.get("label")} for n, d in g.g.nodes(data=True)],
        "edges": [{"from": e.src, "to": e.dst, "kind": e.kind, "prov": e.prov} for e in g.all_edges()],
    }

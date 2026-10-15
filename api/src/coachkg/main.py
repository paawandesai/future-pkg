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

from coachkg.auth import current_coach
from coachkg.config import REPO_ROOT
from coachkg.generator.pipeline import GenerateRequest, run
from coachkg.llm import LLM
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

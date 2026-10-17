"""HTTP API. Request and response bodies are never logged."""

from __future__ import annotations

import contextlib
import hmac
import json
import logging
import os
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from coachkg.access import (
    AccessRequestIn,
    AccessStore,
    AccountExists,
    Accounts,
    CognitoAccounts,
    DynamoAccessStore,
    MemoryAccessStore,
    MemoryAccounts,
    RateLimited,
    client_key,
    normalise_email,
    viewer_network,
)
from coachkg.auth import Admin, current_admin, current_coach
from coachkg.config import ORIGIN_HEADER, REPO_ROOT, origin_secret
from coachkg.copilot import agent, data
from coachkg.generator.pipeline import GenerateRequest, run
from coachkg.llm import KEY_PROBLEM, LLM, LLMAuthError, LLMError, failure_message
from coachkg.member import Member
from coachkg.plans import DynamoPlanStore, PlanStore, SqlitePlanStore
from coachkg.world import World, get_world

# No slash redirects: a redirect's Location would name the function URL behind CloudFront.
app = FastAPI(title="coachkg", docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)


@app.exception_handler(LLMAuthError)
async def _key_problem(_request: Request, _exc: LLMAuthError) -> JSONResponse:
    # Raised while building the client when no key is set at all.
    return JSONResponse(status_code=503, content={"detail": KEY_PROBLEM})


access_log = logging.getLogger("coachkg.access")
if not access_log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    access_log.addHandler(_handler)
    access_log.setLevel(logging.INFO)
    access_log.propagate = False


Next = Callable[[Request], Awaitable[Response]]


def _route(request: Request) -> str:
    return str(getattr(request.scope.get("route"), "path", "unmatched"))


@app.middleware("http")
async def only_via_cloudfront(request: Request, call_next: Next) -> Response:
    """Deployed, every request must carry the header CloudFront adds, so the function URL can't be
    used directly (it would skip CloudFront's headers and let a caller choose X-Forwarded-For).
    /healthz is exempt: the Lambda Web Adapter's readiness check calls it on localhost."""
    if request.url.path != "/healthz":
        try:
            expected = origin_secret()
        except Exception as exc:  # fail closed; the class is enough to diagnose
            access_log.error("origin secret unavailable: %s", type(exc).__name__)
            return JSONResponse(status_code=503, content={"detail": "Service unavailable"})
        sent = request.headers.get(ORIGIN_HEADER, "")
        if expected is not None and not hmac.compare_digest(sent.encode(), expected.encode()):
            return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    return await call_next(request)


@app.middleware("http")
async def log_and_tag(request: Request, call_next: Next) -> Response:
    """One line per request: method, route template, status, milliseconds. No bodies, no query strings.

    Also the catch-all for unhandled errors: it logs the route template and the exception class
    only, because exception messages can carry what a user typed or what a model wrote.
    """
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        access_log.error("unhandled %s on %s %s", type(exc).__name__, request.method, _route(request))
        response = JSONResponse(status_code=500, content={"detail": "Something went wrong. Try again."})
    ms = round((time.perf_counter() - t0) * 1000)
    access_log.info("%s %s %s %dms", request.method, _route(request), response.status_code, ms)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    # Responses hold member data or account state: never stored by a browser or a shared cache.
    response.headers.setdefault("Cache-Control", "no-store")
    return response


Coach = Annotated[str, Depends(current_coach)]


@lru_cache(maxsize=1)
def get_plans() -> PlanStore:
    if table := os.environ.get("PLAN_TABLE"):
        return DynamoPlanStore.from_env(table)
    return SqlitePlanStore(Path(os.environ.get("PLAN_DB", REPO_ROOT / ".cache" / "plans.sqlite3")))


@lru_cache(maxsize=1)
def get_llm() -> LLM:
    return LLM()


@lru_cache(maxsize=1)
def get_access() -> AccessStore:
    if table := os.environ.get("ACCESS_TABLE"):
        return DynamoAccessStore.from_env(table)
    return MemoryAccessStore()


@lru_cache(maxsize=1)
def get_accounts() -> Accounts:
    if os.environ.get("AUTH_MODE") == "cognito" and (pool := os.environ.get("COGNITO_USER_POOL_ID")):
        return CognitoAccounts.from_env(pool)
    return MemoryAccounts()


WorldDep = Annotated[World, Depends(get_world)]
PlansDep = Annotated[PlanStore, Depends(get_plans)]
LLMDep = Annotated[LLM, Depends(get_llm)]
AccessDep = Annotated[AccessStore, Depends(get_access)]
AccountsDep = Annotated[Accounts, Depends(get_accounts)]
AdminDep = Annotated[Admin, Depends(current_admin)]


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
        try:
            async for event in run(world, llm, req, member, coach):
                if event["event"] == "plan":
                    plans.save(event["plan"])
                yield _sse(event)
        except Exception as exc:
            # Headers are already sent, so the middleware can't answer; end the stream with an error
            # event and log the class only.
            access_log.error("unhandled %s in POST /api/generate stream", type(exc).__name__)
            yield _sse({"event": "error", "message": "Something went wrong. Try again."})

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
        "injuries": [
            i.model_dump() | {"active": i.active, "clearable": world.safety.clearable(i)} for i in m.injuries
        ],
        "history": m.workout_history,
        "brief": data.get_brief(ctx),
        "adherence": data.get_adherence(ctx),
        "sleep": data.get_sleep(ctx),
        "labs": data.get_labs(ctx),
        "biomarkers": data.get_biomarkers(ctx),
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


class CopilotTurn(BaseModel):
    """An earlier turn of this conversation, sent back by the client. Quoted to the model as data."""

    role: Literal["coach", "copilot"]
    text: str = Field(max_length=4000)


class CopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    history: list[CopilotTurn] = Field(default_factory=list, max_length=agent.MAX_HISTORY)


@app.post("/api/members/{member_id}/copilot")
async def copilot(
    member_id: str, req: CopilotRequest, coach: Coach, world: WorldDep, llm: LLMDep
) -> dict[str, Any]:
    m = _member(member_id, coach, world)
    model = world.settings.llm_model_main
    if not model:
        raise HTTPException(status_code=503, detail="Model ids are not configured")
    try:
        history = [agent.Turn(t.role, t.text) for t in req.history]
        ans = await agent.ask(llm, model, world.context(m), req.question, history)
    except LLMError as exc:
        detail = failure_message(exc, "The copilot couldn't answer. Try again.")
        raise HTTPException(status_code=502, detail=detail) from None
    return {
        "answer": ans.text,
        "charts": [c.model_dump() for c in ans.charts],
        "tools_used": ans.tools_used,
        "guarded": ans.guarded,
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
    except LLMError as exc:
        detail = failure_message(exc, "Couldn't draft the message. Try again.")
        raise HTTPException(status_code=502, detail=detail) from None


@app.get("/api/members/{member_id}/graph")
def member_graph(member_id: str, coach: Coach, world: WorldDep) -> dict[str, Any]:
    m = _member(member_id, coach, world)
    g = world.member_graphs[m.id]
    return {
        "nodes": [{"id": n, "kind": d.get("kind"), "label": d.get("label")} for n, d in g.g.nodes(data=True)],
        "edges": [{"from": e.src, "to": e.dst, "kind": e.kind, "prov": e.prov} for e in g.all_edges()],
    }


# ---------- demo access: public request form, admin approval ----------


@app.post("/api/access-requests", status_code=202)
def request_access(req: AccessRequestIn, request: Request, access: AccessDep) -> dict[str, str]:
    """Public. The same answer whether or not the email already asked, so the form reveals nothing."""
    # CloudFront sets CloudFront-Viewer-Address itself, and the origin header check means every
    # deployed request came through CloudFront. Without it (local runs) the right-most
    # X-Forwarded-For hops are used; anything to their left is client-supplied, so it is ignored.
    address = viewer_network(request.headers.get("cloudfront-viewer-address"))
    if address is None:
        hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
        address = ",".join(hops[-2:]) or (request.client.host if request.client else None)
    try:
        access.submit(req, client_key(address))
    except RateLimited:
        raise HTTPException(status_code=429, detail="Too many requests right now. Try again later.") from None
    return {"status": "received"}


@app.get("/api/me")
def me(coach: Coach, authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    """What the signed-in person may see: the admin tab appears only for admins."""
    try:
        current_admin(authorization)
        admin = True
    except HTTPException:
        admin = False
    return {"coach_id": coach, "admin": admin}


@app.get("/api/admin/requests")
def admin_requests(admin: AdminDep, access: AccessDep) -> list[dict[str, Any]]:
    return [r.model_dump() for r in access.list()]


@app.post("/api/admin/requests/reject-pending")
def admin_reject_pending(admin: AdminDep, access: AccessDep) -> dict[str, int]:
    """If the public form fills the pending cap, clear it in one go."""
    return {"rejected": access.reject_pending(admin.email)}


@app.post("/api/admin/requests/{request_id}/approve")
def admin_approve(
    request_id: str, admin: AdminDep, access: AccessDep, accounts: AccountsDep
) -> dict[str, Any]:
    pending = access.get(request_id)
    if pending is None or pending.status != "pending":
        raise HTTPException(status_code=404, detail="No pending request with that id")
    with contextlib.suppress(AccountExists):  # already has an account: approving just closes the request
        accounts.invite(pending.email)
    decided = access.decide(request_id, "approved", admin.email)
    if decided is None:
        raise HTTPException(status_code=409, detail="Someone already decided this request")
    return decided.model_dump()


@app.post("/api/admin/requests/{request_id}/reject")
def admin_reject(request_id: str, admin: AdminDep, access: AccessDep) -> dict[str, Any]:
    decided = access.decide(request_id, "rejected", admin.email)
    if decided is None:
        raise HTTPException(status_code=404, detail="No pending request with that id")
    return decided.model_dump()


class InviteIn(BaseModel):
    email: str = Field(min_length=6, max_length=254)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return normalise_email(v)  # a malformed address is a 422, never a 500


@app.get("/api/admin/users")
def admin_users(admin: AdminDep, accounts: AccountsDep) -> list[dict[str, Any]]:
    return [u.model_dump() for u in accounts.list()]


@app.post("/api/admin/users", status_code=201)
def admin_invite(body: InviteIn, admin: AdminDep, accounts: AccountsDep) -> dict[str, str]:
    email = body.email
    try:
        accounts.invite(email)
    except AccountExists:
        raise HTTPException(status_code=409, detail="That email already has an account") from None
    return {"email": email, "status": "invited"}


class UserAction(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    enabled: bool


@app.post("/api/admin/users/enabled")
def admin_set_enabled(body: UserAction, admin: AdminDep, accounts: AccountsDep) -> dict[str, Any]:
    target = next((u for u in accounts.list() if u.email == body.email.strip().lower()), None)
    if target is None:
        raise HTTPException(status_code=404, detail="No such account")
    if target.admin and not body.enabled:
        raise HTTPException(status_code=400, detail="Admin accounts can't be disabled here")
    (accounts.enable if body.enabled else accounts.disable)(target.email)
    return {"email": target.email, "enabled": body.enabled}


@app.post("/api/admin/users/disable-all")
def admin_disable_all(admin: AdminDep, accounts: AccountsDep) -> dict[str, int]:
    """After grading: every reviewer account off; admin accounts stay on."""
    n = 0
    for u in accounts.list():
        if u.enabled and not u.admin:
            accounts.disable(u.email)
            n += 1
    return {"disabled": n}

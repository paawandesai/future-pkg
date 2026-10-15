"""The generator pipeline as a stream of events: read -> filter -> score -> select -> assemble.

Two model calls sit on the path (intent, selection). Everything that decides safety is
deterministic and runs per request. A plan is always a draft until the coach confirms it.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from coachkg.generator import alternatives as alt
from coachkg.generator import assemble, intent, selection, trace
from coachkg.generator.scoring import Focus, Scored, score_candidates
from coachkg.kg.graph import region_node
from coachkg.llm import LLM, CallStats, LLMError
from coachkg.member import Clearance, Member
from coachkg.resolver import Resolution, normalise
from coachkg.safety import SafetyRequest, Side
from coachkg.world import World

POOL_SIZES: dict[assemble.BlockName, int] = {"warmup": 5, "main": 14, "cooldown": 5}


class ConfirmedRegion(BaseModel):
    region: str = Field(description="Region id from a blocker's candidates, e.g. 'knee'")
    side: Side | None = None


class GenerateRequest(BaseModel):
    member_id: str
    prompt: str = Field(min_length=1, max_length=1000)
    minutes: int | None = Field(default=None, ge=10, le=120)
    # Injury ids the coach has cleared for low-impact loading (structured toggle, never from text).
    cleared_low_impact: list[str] = Field(default_factory=list)
    # The coach's answers to "which region did you mean?" blockers.
    confirmed_regions: list[ConfirmedRegion] = Field(default_factory=list)


@dataclass
class Timer:
    t0: float = field(default_factory=time.perf_counter)
    marks: dict[str, int] = field(default_factory=dict)

    def mark(self, name: str) -> int:
        self.marks[name] = int((time.perf_counter() - self.t0) * 1000)
        return self.marks[name]


def _focus(world: World, terms: list[str], hints: list[str]) -> tuple[Focus, list[tuple[str, str | None]]]:
    """Training focus from the request. Hints (region words without a pain cue) count only when
    they are not already part of a focus phrase and they resolve."""
    fp = world.programming.focus_patterns
    focus = Focus()
    rows: list[tuple[str, str | None]] = []
    said = [normalise(t).replace("-", " ") for t in terms]
    todo = [(t, False) for t in terms] + [
        (h, True) for h in hints if not any(normalise(h).replace("-", " ") in s for s in said)
    ]
    for term, is_hint in todo:
        text = normalise(term).replace("-", " ")
        keys = [k for k in fp if k in text]
        if keys:
            sets = [set(fp[k]) for k in keys]
            both = set.intersection(*sets)
            focus.patterns |= both or set.union(*sets)
            label = " ".join(keys)
            if label not in focus.labels:
                focus.labels.append(label)
                rows.append((term, ", ".join(keys)))
            continue
        r = world.resolver.resolve(term, ["muscle", "pattern", "family"])
        if r.status == "accepted" and r.concept:
            kind = r.concept.split(":", 1)[0]
            if kind == "muscle":
                focus.muscles.add(r.concept)
            elif kind == "pattern":
                focus.patterns.add(str(world.store.node(r.concept)["label"]))
            else:
                focus.families.add(r.concept)
            focus.labels.append(str(r.label))
            rows.append((term, r.label))
        elif not is_hint:
            rows.append((term, None))
    return focus, rows


def _restrictive(res: Resolution) -> list[str]:
    """Accepted -> the concept; ambiguous -> every candidate (stricter); no match -> nothing."""
    if res.status == "accepted" and res.concept:
        return [res.concept]
    if res.status == "ambiguous":
        return [c.concept for c in res.candidates]
    return []


def _equipment_containing(world: World, text: str) -> list[str]:
    """Missing equipment is a restriction, so a loose match is the safe reading: "bench" removes
    every bench in the catalog."""
    words = set(normalise(text).split()) - {"a", "the", "her", "his", "their", "any"}
    words = {w[:-1] if w.endswith("s") and len(w) > 4 else w for w in words}
    if not words:
        return []
    return [
        n
        for n in world.store.nodes("equipment")
        if words <= set(normalise(str(world.store.node(n)["label"])).replace("-", " ").split())
    ]


def _member_summary(m: Member) -> dict[str, Any]:
    prefs = m.preferences or {}
    return {
        "goals": [g.get("text") for g in m.goals],
        "dislikes": prefs.get("dislikes", []),
        "preference_notes": prefs.get("notes"),
        "recent_sessions": [
            {"date": w.get("date"), "title": w.get("title"), "completed": w.get("completed")}
            for w in m.workout_history[:3]
        ],
    }


def _item_json(it: assemble.Item, flags: list[str], sc: Scored) -> dict[str, Any]:
    ex = it.exercise
    return {
        "exercise_id": ex.id,
        "name": ex.name,
        "sets": it.sets,
        "reps": it.reps,
        "work_s": it.work_s,
        "rest_s": it.rest_s,
        "each_side": it.each_side,
        "side_note": (
            f"The catalog lists the {ex.laterality}-side row; do both sides." if it.each_side else None
        ),
        "minutes": round(it.seconds / 60, 1),
        "equipment": ex.equipment_required,
        "patterns": ex.movement_patterns,
        "picked_by": it.picked_by,
        "flags": flags,
        "why": sc.why,
        "counted_against": sc.against,
        "path": sc.path,
    }


async def run(
    world: World, llm: LLM, req: GenerateRequest, member: Member, coach_id: str
) -> AsyncIterator[dict[str, Any]]:
    s = world.settings
    timer = Timer()
    calls: list[CallStats] = []
    notes: list[str] = []
    if not (s.llm_model_fast and s.llm_model_main):
        yield {"event": "error", "message": "Model ids are not configured (LLM_MODEL_FAST, LLM_MODEL_MAIN)."}
        return

    # 1. Read the request.
    try:
        it, stats = await intent.extract_intent(llm, s.llm_model_fast, req.prompt)
    except LLMError:
        yield {"event": "error", "message": "Couldn't read the request. Try again."}
        return
    calls.append(stats)
    yield {"event": "stage", "stage": "intent", "ms": timer.mark("intent")}

    # 2. Resolve phrases to graph concepts.
    mentions, hints = intent.merge_mentions(world.resolver, req.prompt, it)
    excl = intent.resolve_terms(world.resolver, it.exclusions, ["family", "exercise", "equipment"])
    equip = intent.resolve_terms(world.resolver, it.unavailable_equipment, ["equipment"])
    exclude_concepts: list[str] = []
    unavailable: list[str] = []
    for r in excl:
        for c in _restrictive(r):
            (unavailable if c.startswith("equipment:") else exclude_concepts).append(c)
        if r.status == "ambiguous":
            notes.append(f'"{r.text}" matched several things; all of them were left out.')
        elif r.status == "no_match":
            hits = _equipment_containing(world, r.text)
            unavailable += hits
            if hits:
                names = ", ".join(sorted(str(world.store.node(h)["label"]) for h in hits))
                notes.append(f'"{r.text}" was read as missing equipment: {names}.')
            else:
                notes.append(
                    f'Couldn\'t match "{r.text}" to an exercise or equipment, so nothing was left out for it.'
                )
    for r in equip:
        hits = _restrictive(r) if r.status == "accepted" else _equipment_containing(world, r.text)
        unavailable += hits
        if r.status != "accepted" and hits:
            names = ", ".join(sorted(str(world.store.node(h)["label"]) for h in hits))
            notes.append(f'"{r.text}" was read as every matching item: {names}.')
        elif not hits:
            notes.append(f'Couldn\'t match "{r.text}" to equipment in the catalog.')
    focus, focus_rows = _focus(world, list(it.focus or []), hints)
    for said, understood in focus_rows:
        if understood is None:
            notes.append(f"Couldn't match \"{said}\" to a training focus, so it didn't shape the plan.")
    read = trace.read_rows(mentions, excl, equip, focus_rows)
    yield {"event": "read", "rows": read}

    # 3. Safety filter (deterministic, per request, emits PROV records).
    now = datetime.now(UTC).isoformat(timespec="seconds")
    clearances = [
        Clearance(injury_id=i.id, cleared_low_impact=True, by=coach_id, at=now)
        for i in member.injuries
        if i.id in req.cleared_low_impact
    ]
    safety = world.safety.run(
        SafetyRequest(
            member=member,
            injury_mentions=mentions,
            exclude_concepts=sorted(set(exclude_concepts)),
            unavailable_equipment=sorted(set(unavailable)),
            clearances=clearances,
            confirmed_regions=[
                (c.region if c.region.startswith("region:") else region_node(c.region), c.side)
                for c in req.confirmed_regions
            ],
        )
    )
    yield {"event": "stage", "stage": "safety", "ms": timer.mark("safety")}
    if safety.blocked:
        yield {
            "event": "blocked",
            "blockers": [
                {"mention": b.mention, "reason": b.reason, "candidates": b.candidates}
                for b in safety.blockers
            ],
            "read": read,
        }
        return

    # 4. Score and 5. pool.
    said_missing = {str(world.store.node(q)["label"]) for q in unavailable}
    blocks_cfg = world.programming.blocks
    alts = alt.find(
        safety,
        world.store,
        focus.patterns,
        focus.muscles,
        said_missing,
        set(blocks_cfg.warmup.patterns) | set(blocks_cfg.cooldown.patterns),
    )
    stands_in: dict[str, str] = {}
    for a in alts:
        stands_in.setdefault(a.use.id, a.instead_of.name)
    scored = score_candidates(
        safety=safety,
        store=world.store,
        resolver=world.resolver,
        member=member,
        focus=focus,
        focus_patterns=world.programming.focus_patterns,
        as_of=s.as_of_date,
        alternatives=stands_in,
    )
    disliked = sorted({x.exercise.name for x in scored if x.disliked})
    if disliked:
        notes.append(
            f"Left out {len(disliked)} exercise(s) the member says they dislike: {', '.join(disliked)}. "
            "Name one in the request to include it."
        )
    scored = [x for x in scored if not x.disliked]
    kept = {x.exercise.id for x in scored}
    alts = [a for a in alts if a.use.id in kept]
    minutes = req.minutes or it.minutes or int(member.preferences.get("preferred_session_minutes", 45))
    budgets = assemble.block_budgets(minutes, world.programming)
    pool = assemble.pools(scored, world.programming, POOL_SIZES)
    if focus and not any(x.focus_match for x in pool["main"]):
        notes.append(
            f"Nothing matching {', '.join(focus.labels)} passed the safety filter, "
            "so the main block uses the closest safe exercises."
        )

    # 6. Selection among safe candidates only.
    try:
        sel = await selection.select(
            llm, s.llm_model_main, req.prompt, _member_summary(member), pool, budgets, world.programming
        )
    except LLMError:
        yield {"event": "error", "message": "Couldn't order the exercises. Try again."}
        return
    if sel.stats:
        calls.append(sel.stats)
    if sel.dropped:
        notes.append(f"Dropped {len(sel.dropped)} id(s) the model returned that were not on the safe list.")
    yield {"event": "stage", "stage": "selection", "ms": timer.mark("selection")}

    # Time budget is enforced after selection.
    fitted = assemble.fit(sel.chosen, pool, budgets, world.programming)
    by_id = {x.exercise.id: x for x in scored}
    blocks = []
    planned_s = 0
    for b in assemble.BLOCKS:
        items = fitted[b]
        planned_s += sum(i.seconds for i in items)
        blocks.append(
            {
                "name": b,
                "budget_minutes": round(budgets[b] / 60, 1),
                "minutes": round(sum(i.seconds for i in items) / 60, 1),
                "items": [
                    _item_json(
                        i,
                        [d.reason for d in safety.flags_for(i.exercise.id)],
                        by_id[i.exercise.id],
                    )
                    for i in items
                ],
            }
        )
    if planned_s < (minutes - 3) * 60:
        notes.append(
            f"Planned {round(planned_s / 60)} of {minutes} minutes: "
            "not enough safe exercises to fill the time."
        )
    if not fitted["main"]:
        notes.append("No exercise fit the main block. Check the exclusions and the member's equipment.")

    plan: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "member_id": member.id,
        "coach_id": coach_id,
        "status": "draft",
        "created_at": now,
        "title": f"{', '.join(focus.labels) or 'Full body'} · {minutes} min".capitalize(),
        "label": "Coach decision support: a draft for the coach to review and confirm.",
        "minutes_requested": minutes,
        "minutes_planned": round(planned_s / 60, 1),
        "blocks": blocks,
        "trace": {
            "read": read,
            "restrictions": trace.restriction_rows(safety),
            "excluded": trace.excluded_groups(safety, world.rules),
            "alternatives": [a.json() for a in alts],
            "unverified": trace.unverified_lines(safety, world.programming.review.trusted),
            "notes": notes,
            "model_calls": [
                {
                    "purpose": c.purpose,
                    "model": c.served_by,
                    "ms": c.ms,
                    "in": c.input_tokens,
                    "out": c.output_tokens,
                }
                for c in calls
            ],
            "prov": safety.prov,
        },
        "timings_ms": {**timer.marks, "total": timer.mark("total")},
    }
    yield {"event": "plan", "plan": plan}

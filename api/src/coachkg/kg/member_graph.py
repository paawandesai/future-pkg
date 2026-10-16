"""Member graph (KG 2): one member's record as typed, dated nodes and edges.

Every field family of the member record is ingested: profile, goals, preferences (and dislikes),
equipment, injuries, workout history, weekly adherence, biomarkers, labs and DEXA, chat history
(with image captions) and the provided coach brief. The schema and the joins to the movement
graph (KG 1) are documented in docs/schema.md.

KG 2 joins KG 1 only through shared concept nodes: equipment, body regions and exercises (plus
families and patterns for dislikes). Shared nodes are copied from KG 1 with the same id.

Provenance: record fields are `dataset`; chat lines and their attachments are `member-said` or
`coach-said`. The provided coach brief is `dataset` text, and its churn level is stored as a
claim (`churn_claim`, edge `claims`), never as a computed fact. The safety filter never reads this
graph's chat edges, so a member's words cannot clear an injury. Labs and DEXA are stored as
values only: no ranges, flags or derived nodes.

The copilot's read-only tools (copilot/data.py) answer from this graph through the accessors at
the bottom of this module.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from coachkg.kg.graph import Edge, NetworkXStore
from coachkg.member import Member
from coachkg.resolver import Resolver
from coachkg.safety import SafetyFilter

SOURCE = "member-context.json"
PROFILE_FIELDS = (
    "age",
    "sex",
    "height_cm",
    "weight_kg",
    "timezone",
    "member_since",
    "coach_id",
    "tier",
)
BIOMARKER_UNITS = {"resting_hr_bpm": "bpm", "hrv_ms": "ms"}


def member_node(member_id: str) -> str:
    return f"member:{member_id}"


def build_member_graph(
    member: Member,
    movement: NetworkXStore,
    resolver: Resolver,
    safety: SafetyFilter,
    as_of: date,
    source: str = SOURCE,
) -> NetworkXStore:
    g = NetworkXStore()
    mid = member_node(member.id)
    g.add_node(
        mid,
        kind="member",
        label=member.name,
        fictional=True,
        member_id=member.id,
        as_of=as_of.isoformat(),
        **{k: member.profile.get(k) for k in PROFILE_FIELDS},
    )

    def shared(node: str) -> None:
        if node not in g.g:
            g.add_node(node, **movement.node(node))

    def edge(src: str, dst: str, kind: str, field: str, prov: str = "dataset", **attrs: Any) -> None:
        g.add_edge(Edge(src, dst, kind, prov, f"{source} {field}", attrs))

    def link_body_mentions(src: str, text: str, kind: str, field: str, prov: str) -> None:
        for bm in resolver.find_body_mentions(text.replace("-", " ")):
            if bm.resolution.status == "accepted" and bm.resolution.concept:
                shared(bm.resolution.concept)
                edge(src, bm.resolution.concept, kind, field, prov)

    # Goals: dated by their target date; body regions they name join KG 1.
    for i, goal in enumerate(member.goals):
        node = f"goal:{goal.get('id') or i}"
        g.add_node(
            node,
            kind="goal",
            index=i,
            label=goal.get("text"),
            text=goal.get("text"),
            priority=goal.get("priority"),
            target_date=goal.get("target_date"),
        )
        edge(mid, node, "has-goal", "goals")
        link_body_mentions(node, str(goal.get("text") or ""), "concerns", "goals.text", "dataset")

    # Preferences, and each dislike as its own node joined to the KG 1 concept it names.
    prefs = member.preferences or {}
    pnode = f"preferences:{member.id}"
    g.add_node(
        pnode,
        kind="preferences",
        label="Preferences",
        **{k: v for k, v in prefs.items() if k != "dislikes"},
    )
    edge(mid, pnode, "has-preferences", "preferences")
    for i, text in enumerate(prefs.get("dislikes") or []):
        node = f"dislike:{i}"
        g.add_node(node, kind="dislike", index=i, label=str(text))
        edge(mid, node, "dislikes", "preferences.dislikes")
        r = resolver.resolve(str(text), ["family", "exercise", "pattern"])
        if r.status == "accepted" and r.concept:
            shared(r.concept)
            edge(node, r.concept, "refers-to", "preferences.dislikes", match=r.method)

    # Equipment: resolved items join the KG 1 equipment node; the rest stay as recorded text.
    for i, q in enumerate(member.equipment_available):
        r = resolver.resolve(q, ["equipment"])
        if r.status == "accepted" and r.concept:
            shared(r.concept)
            edge(mid, r.concept, "has-equipment", "equipment_available", as_recorded=q, index=i)
        else:
            node = f"equipment-unresolved:{i}"
            g.add_node(node, kind="equipment_unresolved", index=i, label=q)
            edge(mid, node, "has-equipment-unresolved", "equipment_available")

    # Injuries, dated by onset, located at a KG 1 region.
    for inj in member.injuries:
        node = f"injury:{inj.id}"
        g.add_node(
            node,
            kind="injury",
            label=inj.region,
            injury_id=inj.id,
            region_text=inj.region,
            joint=inj.joint,
            status=inj.status,
            severity=inj.severity,
            since=inj.since.isoformat() if inj.since else None,
            date=inj.since.isoformat() if inj.since else None,
            notes=inj.notes,
            active=inj.active,
        )
        edge(mid, node, "has-injury", "injuries")
        region = safety.region_for_injury(inj.joint, inj.region)
        if region and region in movement.g:
            shared(region)
            edge(node, region, "located-at", "injuries.joint")

    # Workout history: dated sessions, each exercise joined to a KG 1 exercise when it resolves.
    for i, w in enumerate(member.workout_history):
        node = f"session:{w['date']}"
        n = 2
        while node in g.g:
            node = f"session:{w['date']}#{n}"
            n += 1
        g.add_node(
            node,
            kind="session",
            index=i,
            label=w.get("title"),
            date=w["date"],
            title=w.get("title"),
            planned=w.get("planned"),
            completed=w.get("completed"),
            duration_min=w.get("duration_min"),
            rpe=w.get("rpe"),
            exercises=list(w.get("exercises", [])),
        )
        edge(mid, node, "scheduled", "workout_history")
        for pos, name in enumerate(w.get("exercises", [])):
            r = resolver.resolve(str(name), ["exercise"])
            if r.status == "accepted" and r.concept:
                shared(r.concept)
                edge(
                    node,
                    r.concept,
                    "included",
                    "workout_history",
                    match=r.method,
                    as_recorded=name,
                    position=pos,
                )

    # Weekly adherence: one dated node per week.
    adherence = member.adherence or {}
    g.add_node(mid, adherence_trend=adherence.get("trend"))
    for wk in adherence.get("weekly_completion_pct", []):
        node = f"adherence:{wk['week_of']}"
        g.add_node(
            node,
            kind="adherence_week",
            label=f"{wk['pct']}%",
            date=wk["week_of"],
            week_of=wk["week_of"],
            pct=wk["pct"],
        )
        edge(mid, node, "has-adherence", "adherence.weekly_completion_pct")

    # Biomarkers. Resting HR and HRV come without a date: stored undated, reported as of AS_OF.
    bio = member.biomarkers or {}
    for key, unit in BIOMARKER_UNITS.items():
        if bio.get(key) is not None:
            node = f"biomarker:{key}"
            g.add_node(
                node,
                kind="biomarker",
                label=key,
                metric=key,
                value=bio[key],
                unit=unit,
                date=None,
                reported_as_of=as_of.isoformat(),
            )
            edge(mid, node, "has-biomarker", f"biomarkers.{key}")
    hours = bio.get("sleep_hours_last_7_days", [])
    start = as_of - timedelta(days=len(hours))
    for i, h in enumerate(hours):
        d = (start + timedelta(days=i)).isoformat()
        node = f"sleep:{d}"
        g.add_node(node, kind="sleep_night", label=f"{h} h", date=d, hours=h, date_assigned=True)
        edge(mid, node, "slept", "biomarkers.sleep_hours_last_7_days")
    for w in bio.get("weight_trend_kg", []):
        node = f"weight:{w['date']}"
        g.add_node(node, kind="weight_reading", label=f"{w['kg']} kg", date=w["date"], kg=w["kg"])
        edge(mid, node, "has-weight", "biomarkers.weight_trend_kg")

    # Labs and DEXA: values only, as recorded. No ranges, flags or interpretation.
    for panel, values in (member.labs or {}).items():
        if not isinstance(values, dict):
            continue
        pnode = f"lab-panel:{panel}"
        g.add_node(pnode, kind="lab_panel", label=panel, panel=panel, date=values.get("date"))
        edge(mid, pnode, "has-lab-panel", f"labs.{panel}")
        for i, (name, value) in enumerate(values.items()):
            if name == "date":
                continue
            vnode = f"lab-value:{panel}:{name}"
            g.add_node(
                vnode, kind="lab_value", index=i, label=name, name=name, value=value, date=values.get("date")
            )
            edge(pnode, vnode, "has-value", f"labs.{panel}.{name}")

    # Chat: dated messages with provenance; image attachments are captions only.
    for i, m in enumerate(member.chat_history):
        node = f"message:{i}"
        day = datetime.fromisoformat(m.ts).date().isoformat() if m.ts else None
        g.add_node(node, kind="message", index=i, ts=m.ts, date=day, provenance=m.provenance, quote=m.text)
        edge(mid, node, "sent" if m.provenance == "member-said" else "received", "chat_history", m.provenance)
        for j, a in enumerate(m.attachments or []):
            anode = f"attachment:{i}:{j}"
            g.add_node(
                anode,
                kind="attachment",
                index=j,
                label=a.get("caption"),
                type=a.get("type"),
                caption=a.get("caption"),
                provenance=m.provenance,
            )
            edge(node, anode, "has-attachment", "chat_history.attachments", m.provenance)
        link_body_mentions(node, m.text, "mentions", "chat_history", m.provenance)

    # The provided coach brief: tasks as written, churn level as a claim the brief makes.
    brief = member.coach_brief or {}
    if brief:
        bnode = f"brief:{brief.get('generated_for') or 'undated'}"
        g.add_node(bnode, kind="coach_brief", label="Coach brief", date=brief.get("generated_for"))
        edge(mid, bnode, "has-brief", "coach_brief")
        for i, t in enumerate(brief.get("morning_tasks", [])):
            tnode = f"task:{i}"
            g.add_node(
                tnode,
                kind="morning_task",
                index=i,
                label=t.get("type"),
                type=t.get("type"),
                text=t.get("text"),
            )
            edge(bnode, tnode, "has-task", "coach_brief.morning_tasks")
        if brief.get("churn_risk"):
            cr = brief["churn_risk"]
            cnode = "claim:churn"
            g.add_node(
                cnode,
                kind="churn_claim",
                label=f"Brief says churn risk {cr.get('level')}",
                level=cr.get("level"),
                reasons=list(cr.get("reasons", [])),
                raw=cr,
            )
            edge(bnode, cnode, "claims", "coach_brief.churn_risk", asserted_by="coach_brief")
    return g


# ---------- accessors (read-only) used by the copilot tools ----------


def _sorted(g: NetworkXStore, nodes: list[str], key: str) -> list[dict[str, Any]]:
    rows = [g.node(n) | {"id": n} for n in nodes]
    return sorted(rows, key=lambda d: (d.get(key) is None, d.get(key)))


def linked(g: NetworkXStore, src: str, kind: str, order: str = "index") -> list[dict[str, Any]]:
    """Nodes at the end of `kind` edges from `src`, ordered by an attribute (index or date)."""
    return _sorted(g, [e.dst for e in g.out_edges(src, kind)], order)


def member_attrs(g: NetworkXStore) -> dict[str, Any]:
    (mid,) = g.nodes("member")
    return g.node(mid) | {"id": mid}


def of_member(g: NetworkXStore, kind: str, order: str = "index") -> list[dict[str, Any]]:
    return linked(g, member_attrs(g)["id"], kind, order)

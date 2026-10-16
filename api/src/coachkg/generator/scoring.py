"""Step 4: deterministic ranking of already-safe candidates. Ranking reasons are not safety reasons."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from coachkg.data import Exercise
from coachkg.generator.programming import Programming
from coachkg.kg.graph import NetworkXStore, ex_node
from coachkg.member import Member
from coachkg.resolver import Resolver, normalise
from coachkg.safety import SafetyResult


@dataclass
class Focus:
    patterns: set[str] = field(default_factory=set)  # dataset pattern labels
    muscles: set[str] = field(default_factory=set)  # muscle:* nodes
    families: set[str] = field(default_factory=set)  # family:* nodes
    labels: list[str] = field(default_factory=list)  # what the coach asked for, for the title

    def __bool__(self) -> bool:
        return bool(self.patterns or self.muscles or self.families)


@dataclass
class Scored:
    exercise: Exercise
    score: float
    why: list[str]  # reasons it ranked up
    focus_match: bool
    against: list[str] = field(default_factory=list)  # reasons it ranked down
    # Graph edges behind `why`. Each edge has src, kind, dst and a `role`: focus, equipment,
    # member-owns, region-clear, region-cleared or block. Every candidate gets the equipment and
    # region edges; focus edges only on a focus match; block edges once the plan places it.
    path: list[dict[str, str]] = field(default_factory=list)
    disliked: str | None = None  # the member's dislike it matches, unless the coach asked for it


def _families(store: NetworkXStore, ex: Exercise) -> set[str]:
    out: set[str] = set()
    stack = [e.dst for e in store.out_edges(ex_node(ex.id), "variant-of")]
    while stack:
        f = stack.pop()
        if f not in out:
            out.add(f)
            stack += [e.dst for e in store.out_edges(f, "is-a")]
    return out


def _muscles(store: NetworkXStore, ex: Exercise) -> set[str]:
    return {e.dst for e in store.out_edges(ex_node(ex.id), "targets")}


def _edge(src: str, kind: str, dst: str, role: str) -> dict[str, str]:
    return {"src": src, "kind": kind, "dst": dst, "role": role}


def _pattern_node(p: str) -> str:
    return f"pattern:{p.strip().lower()}"


def eligibility_path(
    store: NetworkXStore, member: Member, ex: Exercise, safety: SafetyResult
) -> tuple[list[str], list[dict[str, str]]]:
    """Why a candidate was eligible at all, as positive graph paths: what it requires and that the
    member has it, and which regions it stresses and why none of them stopped it. These restate
    what the safety filter already decided; they never add or remove a safety decision."""
    node = ex_node(ex.id)
    member_node = f"member:{member.id}"
    why: list[str] = []
    path: list[dict[str, str]] = []
    needs = store.out_edges(node, "requires")
    for e in needs:
        path.append(_edge(node, "requires", e.dst, "equipment"))
        path.append(_edge(member_node, "has-equipment", e.dst, "member-owns"))
    if needs:
        labels = ", ".join(sorted(str(store.node(e.dst)["label"]) for e in needs))
        why.append(f"uses only equipment the member has ({labels})")
    else:
        why.append("needs no equipment")
    cleared = {
        (ev["from"], ev["to"])
        for d in safety.flags_for(ex.id)
        if d.outcome == "downranked"
        for ev in d.evidence
        if ev["edge"] == "stresses"
    }
    stressed: list[str] = []
    for e in store.out_edges(node, "stresses"):
        role = "region-cleared" if (e.src, e.dst) in cleared else "region-clear"
        path.append(_edge(node, "stresses", e.dst, role))
        if role == "region-clear":
            stressed.append(str(store.node(e.dst)["label"]).lower())
    if cleared:
        why.append("loads a restricted region only within the coach's low-impact clearance")
    if stressed:
        names = sorted(set(stressed))
        regions = ", ".join(names)
        if not safety.restrictions:
            why.append(f"loads {regions}; no restriction applies")
        elif len(names) == 1:
            why.append(f"loads {regions}, which is not restricted")
        else:
            why.append(f"loads {regions}, none of them restricted")
    return why, path


def block_path(sc: Scored, block: str, prog: Programming, picked_by: str) -> tuple[str, list[dict[str, str]]]:
    """Which plan stage placed the exercise, with the movement-pattern edges it was placed by.
    Warm-up and cool-down come from the block patterns in kg/rules/programming.yaml."""
    node = ex_node(sc.exercise.id)
    pats = list(sc.exercise.movement_patterns)
    if block in ("warmup", "cooldown"):
        listed = set(getattr(prog.blocks, block).patterns)
        hit = [p for p in pats if p in listed] or pats
        name = "warm-up" if block == "warmup" else "cool-down"
        line = (
            f"{hit[0]} is a {name} pattern in programming.yaml"
            if len(hit) == 1
            else f"{', '.join(hit)} are {name} patterns in programming.yaml"
        )
    else:
        hit = pats
        line = (
            "picked for the main block by the selection step"
            if picked_by == "selection"
            else "added to the main block to fill the time window"
        )
    return line, [_edge(node, "has-pattern", _pattern_node(p), "block") for p in hit]


def _goal_patterns(member: Member, focus_patterns: dict[str, list[str]]) -> set[str]:
    out: set[str] = set()
    for g in member.goals:
        if g.get("priority") != 1:
            continue
        text = normalise(str(g.get("text", ""))).replace("-", " ")
        for key, pats in focus_patterns.items():
            if key in text:
                out |= set(pats)
    return out


def _recent_patterns(member: Member, resolver: Resolver, store: NetworkXStore, as_of: date) -> set[str]:
    """Patterns trained in the two days before as_of (history names resolved to catalog exercises)."""
    out: set[str] = set()
    for w in member.workout_history:
        try:
            days = (as_of - date.fromisoformat(str(w.get("date")))).days
        except ValueError:
            continue
        if not (0 <= days <= 2) or not w.get("completed"):
            continue
        for name in w.get("exercises", []):
            r = resolver.resolve(str(name), ["exercise"])
            if r.status == "accepted" and r.concept:
                out |= set(store.node(r.concept)["exercise"].movement_patterns)
    return out


def score_candidates(
    *,
    safety: SafetyResult,
    store: NetworkXStore,
    resolver: Resolver,
    member: Member,
    focus: Focus,
    focus_patterns: dict[str, list[str]],
    as_of: date,
    alternatives: dict[str, str] | None = None,
) -> list[Scored]:
    """`alternatives` maps a safe exercise id to the excluded exercise it can stand in for."""
    goal_pats = _goal_patterns(member, focus_patterns)
    recent = _recent_patterns(member, resolver, store, as_of)
    prefs = member.preferences or {}
    notes = normalise(str(prefs.get("notes", "")))
    liked_equipment = {q for q in member.equipment_available if normalise(q) in notes}
    disliked: dict[str, str] = {}
    for text in prefs.get("dislikes", []):
        r = resolver.resolve(str(text), ["family", "exercise"])
        if r.status == "accepted" and r.concept:
            disliked[r.concept] = str(text)

    out: list[Scored] = []
    for ex in safety.candidates:
        s, why, against, path = 0.0, [], [], []
        node = ex_node(ex.id)
        fams = _families(store, ex)
        pats = set(ex.movement_patterns)
        muscles = _muscles(store, ex)
        match = False
        if focus:
            for p in sorted(pats & focus.patterns):
                path.append(_edge(node, "has-pattern", _pattern_node(p), "focus"))
            for m in sorted(muscles & focus.muscles):
                path.append(_edge(node, "targets", m, "focus"))
            for f in sorted(fams & focus.families):
                path.append(_edge(node, "variant-of", f, "focus"))
            match = bool(path)
        if match:
            s += 3
            why.append("matches the requested focus")
        if pats & goal_pats:
            s += 1.5
            why.append("fits a priority-1 goal")
        if liked_equipment & set(ex.equipment_required):
            s += 1
            why.append("uses equipment the member prefers")
        if alternatives and ex.id in alternatives:
            s += 1
            why.append(f"stands in for {alternatives[ex.id]}, which needs equipment the member lacks")
        hit = next((label for n, label in disliked.items() if n in fams or n == node), None)
        asked_for = bool(fams & focus.families) or node in focus.families
        if hit and asked_for:
            against.append(f"member dislikes {hit} (kept because the request asks for it)")
        if pats & recent:
            s -= 1.5
            against.append("same pattern trained in the last two days")
        for d in safety.flags_for(ex.id):
            s -= 2 if d.outcome == "downranked" else 0.5
            against.append(d.reason)
        fit_why, fit_path = eligibility_path(store, member, ex, safety)
        why += fit_why
        path += fit_path
        out.append(Scored(ex, s, why, match, against, path, hit if hit and not asked_for else None))
    out.sort(key=lambda x: (-x.score, x.exercise.name))
    return out

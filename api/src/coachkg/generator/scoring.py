"""Step 4: deterministic ranking of already-safe candidates. Ranking reasons are not safety reasons."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from coachkg.data import Exercise
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
    path: list[dict[str, str]] = field(default_factory=list)  # graph edges behind `why`
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
                path.append({"src": node, "kind": "has-pattern", "dst": f"pattern:{p.strip().lower()}"})
            for m in sorted(muscles & focus.muscles):
                path.append({"src": node, "kind": "targets", "dst": m})
            for f in sorted(fams & focus.families):
                path.append({"src": node, "kind": "variant-of", "dst": f})
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
        out.append(Scored(ex, s, why, match, against, path, hit if hit and not asked_for else None))
    out.sort(key=lambda x: (-x.score, x.exercise.name))
    return out

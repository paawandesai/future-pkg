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
    why: list[str]
    focus_match: bool


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
) -> list[Scored]:
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
        s, why = 0.0, []
        fams = _families(store, ex)
        pats = set(ex.movement_patterns)
        match = bool(
            focus and (pats & focus.patterns or _muscles(store, ex) & focus.muscles or fams & focus.families)
        )
        if match:
            s += 3
            why.append("matches the requested focus")
        if pats & goal_pats:
            s += 1.5
            why.append("fits a priority-1 goal")
        if liked_equipment & set(ex.equipment_required):
            s += 1
            why.append("uses equipment the member prefers")
        hit = next(
            (label for node, label in disliked.items() if node in fams or node == ex_node(ex.id)), None
        )
        if hit:
            s -= 3
            why.append(f"member dislikes {hit}")
        if pats & recent:
            s -= 1.5
            why.append("same pattern trained in the last two days")
        for d in safety.flags_for(ex.id):
            s -= 2 if d.outcome == "downranked" else 0.5
            why.append(d.reason)
        out.append(Scored(ex, s, why, match))
    out.sort(key=lambda x: (-x.score, x.exercise.name))
    return out

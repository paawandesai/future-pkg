"""Equivalent alternatives for exercises left out only because the member lacks the equipment.

An alternative must already be on the safe list, share a movement pattern and a target muscle
with the exercise it replaces, and is found by walking the graph:

    excluded --has-pattern--> pattern <--has-pattern-- alternative
    excluded --targets------> muscle  <--targets------ alternative

When the signed equipment file has a `substitutes-for` edge from the alternative's equipment to
the missing item, for that pattern, the alternative ranks first and the edge is shown. This is
ranking only: the safety filter has already decided what is allowed, and this never adds to it.
"""

from __future__ import annotations

from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from typing import Any

from coachkg.data import Exercise
from coachkg.kg.graph import NetworkXStore, ex_node
from coachkg.safety import SafetyResult

PER_EXCLUDED = 2
MAX_TOTAL = 6


@dataclass
class Alternative:
    instead_of: Exercise
    use: Exercise
    needs: list[str]
    patterns: list[str]
    muscles: list[str]
    substitute: tuple[str, str] | None  # (use equipment, missing equipment) from a signed edge
    path: list[dict[str, str]] = field(default_factory=list)

    def json(self) -> dict[str, Any]:
        return {
            "instead_of": self.instead_of.name,
            "instead_of_id": self.instead_of.id,
            "needs": self.needs,
            "use": self.use.name,
            "use_id": self.use.id,
            "shared_patterns": self.patterns,
            "shared_muscles": self.muscles,
            "substitute": (
                {"use": self.substitute[0], "for": self.substitute[1], "source": "kg/rules/equipment.yaml"}
                if self.substitute
                else None
            ),
            "path": self.path,
        }


def _dst(store: NetworkXStore, ex: Exercise, kind: str) -> set[str]:
    return {e.dst for e in store.out_edges(ex_node(ex.id), kind)}


def _label(store: NetworkXStore, node: str) -> str:
    return str(store.node(node).get("label", node.split(":", 1)[-1]))


def _equipment_only(safety: SafetyResult) -> dict[str, list[str]]:
    """Exercise id -> missing equipment, for exercises whose every exclusion is missing equipment."""
    needs: dict[str, list[str]] = {}
    other: set[str] = set()
    for d in safety.decisions:
        if d.outcome != "excluded":
            continue
        if d.reason.startswith("Needs ") and d.rule is None:
            needs.setdefault(d.exercise_id, []).extend(d.reason.removeprefix("Needs ").split(", "))
        else:
            other.add(d.exercise_id)
    return {k: v for k, v in needs.items() if k not in other}


def find(
    safety: SafetyResult,
    store: NetworkXStore,
    focus_patterns: set[str],
    focus_muscles: set[str],
    said_missing: set[str],
    edge_patterns: AbstractSet[str] = frozenset(),
) -> list[Alternative]:
    """Alternatives for exercises left out for equipment the request said is missing, or, when the
    request named a focus, for on-focus exercises the member lacks equipment for.

    `edge_patterns` are the warm-up and cool-down patterns: a main-block exercise is only replaced
    by another main-block exercise, so a press is never "replaced" by a neck circle."""
    missing_ids = _equipment_only(safety)
    if not missing_ids:
        return []
    safe = safety.candidates
    safe_pats = {ex.id: _dst(store, ex, "has-pattern") for ex in safe}
    safe_musc = {ex.id: _dst(store, ex, "targets") for ex in safe}

    excluded: list[Exercise] = []
    for ex_id in missing_ids:
        if ex_node(ex_id) in store.g:
            excluded.append(store.node(ex_node(ex_id))["exercise"])

    def on_focus(ex: Exercise) -> bool:
        return bool(set(ex.movement_patterns) & focus_patterns or _dst(store, ex, "targets") & focus_muscles)

    def said(ex: Exercise) -> bool:
        return bool(set(missing_ids[ex.id]) & said_missing)

    wanted = [ex for ex in excluded if said(ex) or on_focus(ex)]
    out: list[Alternative] = []
    used: set[str] = set()  # each stand-in is offered once, for the exercise it fits best
    for ex in sorted(wanted, key=lambda e: (not (said(e) and on_focus(e)), not said(e), e.name)):
        pats = _dst(store, ex, "has-pattern")
        musc = _dst(store, ex, "targets")
        ranked: list[tuple[tuple[int, int, int, str], Alternative]] = []
        main = not set(ex.movement_patterns) & edge_patterns
        for cand in safe:
            if cand.id in used:
                continue
            if main and set(cand.movement_patterns) & edge_patterns:
                continue
            shared_p = sorted(pats & safe_pats[cand.id])
            shared_m = sorted(musc & safe_musc[cand.id])
            if not shared_p or not shared_m:
                continue
            sub = _substitute(store, cand, set(missing_ids[ex.id]), {_label(store, p) for p in shared_p})
            alt = Alternative(
                instead_of=ex,
                use=cand,
                needs=missing_ids[ex.id],
                patterns=[_label(store, p) for p in shared_p],
                muscles=[_label(store, m) for m in shared_m],
                substitute=sub,
                path=_path(ex, cand, shared_p[0], shared_m[0], sub),
            )
            key = (0 if sub else 1, -len(shared_p), -len(shared_m), cand.name)
            ranked.append((key, alt))
        ranked.sort(key=lambda r: r[0])
        picked = [a for _, a in ranked[:PER_EXCLUDED]]
        used |= {a.use.id for a in picked}
        out += picked
        if len(out) >= MAX_TOTAL:
            return out[:MAX_TOTAL]
    return out


def _substitute(
    store: NetworkXStore, cand: Exercise, missing: set[str], shared_patterns: set[str]
) -> tuple[str, str] | None:
    for q in cand.equipment_required:
        use = f"equipment:{q.strip().lower()}"
        if use not in store.g:
            continue
        for e in store.out_edges(use, "substitutes-for"):
            if _label(store, e.dst) in missing and shared_patterns & set(e.attrs.get("patterns", [])):
                return (q, _label(store, e.dst))
    return None


def _path(
    ex: Exercise, cand: Exercise, pattern: str, muscle: str, sub: tuple[str, str] | None
) -> list[dict[str, str]]:
    path = [
        {"src": ex_node(ex.id), "kind": "has-pattern", "dst": pattern},
        {"src": ex_node(cand.id), "kind": "has-pattern", "dst": pattern},
        {"src": ex_node(ex.id), "kind": "targets", "dst": muscle},
        {"src": ex_node(cand.id), "kind": "targets", "dst": muscle},
    ]
    if sub:
        path.append(
            {
                "src": f"equipment:{sub[0].strip().lower()}",
                "kind": "substitutes-for",
                "dst": f"equipment:{sub[1].strip().lower()}",
            }
        )
    return path

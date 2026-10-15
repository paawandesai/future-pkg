"""Step 7: render the trace from records the pipeline already made. Template only, no model:
every sentence here comes from a filter decision, a resolver result or a scoring rule."""

from __future__ import annotations

from typing import Any

from coachkg.kg.rules import RuleSet
from coachkg.resolver import BodyMention, Resolution
from coachkg.safety import SafetyResult


def _label(store_label: str | None, side: str | None) -> str:
    if not store_label:
        return "nothing"
    return f"{store_label} ({side})" if side and side != "both" else store_label


def read_rows(
    mentions: list[BodyMention],
    exclusions: list[Resolution],
    equipment: list[Resolution],
    focus: list[tuple[str, str | None]],
) -> list[dict[str, Any]]:
    """How each phrase of the request was understood, with the match method and confidence."""
    rows: list[dict[str, Any]] = []
    for m in mentions:
        r = m.resolution
        rows.append(
            {
                "kind": "injury",
                "said": m.text,
                "understood_as": _label(r.label, m.side),
                "status": r.status,
                "method": r.method,
                "confidence": round(r.score, 2),
            }
        )
    for kind, items in (("exclusion", exclusions), ("equipment", equipment)):
        for r in items:
            rows.append(
                {
                    "kind": kind,
                    "said": r.text,
                    "understood_as": r.label or "nothing",
                    "status": r.status,
                    "method": r.method,
                    "confidence": round(r.score, 2),
                }
            )
    for said, understood in focus:
        rows.append(
            {
                "kind": "focus",
                "said": said,
                "understood_as": understood or "nothing",
                "status": "accepted" if understood else "no_match",
                "method": "exact" if understood else "none",
                "confidence": 1.0 if understood else 0.0,
            }
        )
    return rows


def excluded_groups(safety: SafetyResult, rules: RuleSet) -> list[dict[str, Any]]:
    by_rule = {r.id: r for r in rules.rules}
    groups: dict[tuple[str, str | None], dict[str, Any]] = {}
    equipment: list[dict[str, str]] = []
    for d in safety.decisions:
        if d.outcome != "excluded":
            continue
        if d.reason.startswith("Needs ") and d.rule is None:
            equipment.append({"name": d.name, "detail": d.reason})
            continue
        g = groups.setdefault(
            (d.reason, d.rule),
            {"reason": d.reason, "rule": d.rule, "exercises": [], "trusted": True, "sources": []},
        )
        if d.name not in g["exercises"]:
            g["exercises"].append(d.name)
        g["trusted"] = g["trusted"] and d.trusted
        rule = by_rule.get(d.rule or "")
        if rule and not g["sources"]:
            g["sources"] = [
                {"short": c.short or c.dataset, "doi": c.doi, "checked": c.checked} for c in rule.citations
            ]
    out = sorted(groups.values(), key=lambda g: (-len(g["exercises"]), g["reason"]))
    for g in out:
        g["exercises"].sort()
    if equipment:
        out.append(
            {
                "reason": "Needs equipment the member does not have",
                "rule": None,
                "exercises": sorted(e["name"] for e in equipment),
                "details": sorted(equipment, key=lambda e: e["name"]),
                "trusted": True,
                "sources": [
                    {"short": "member equipment list and exercises.json", "doi": None, "checked": True}
                ],
            }
        )
    return out


def unverified_lines(safety: SafetyResult, programming_signed: bool) -> list[str]:
    """One line per distinct unverified reason, not one per exercise."""
    counts: dict[str, int] = {}
    file_lines: list[str] = []
    for line in safety.unverified:
        if ": " in line and not line.startswith("kg/"):
            reason = line.split(": ", 1)[1]
            counts[reason] = counts.get(reason, 0) + 1
        else:
            file_lines.append(line)
    out = [f"{reason} ({n} exercise{'s' if n != 1 else ''})" for reason, n in counts.items()]
    out += file_lines
    if not programming_signed:
        out.append("Sets, reps and rest are model-drafted defaults (kg/rules/programming.yaml is unsigned).")
    return out


def restriction_rows(safety: SafetyResult) -> list[dict[str, Any]]:
    return [
        {
            "regions": sorted(r.regions),
            "side": r.side,
            "condition": r.condition,
            "from": r.origin,
            "confidence": r.confidence,
        }
        for r in safety.restrictions
    ]

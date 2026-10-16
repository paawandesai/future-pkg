"""Step 7: render the trace from records the pipeline already made. Template only, no model:
every sentence here comes from a filter decision, a resolver result or a scoring rule."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from coachkg.kg.rules import RuleSet
from coachkg.llm import CallStats
from coachkg.resolver import BodyMention, Resolution
from coachkg.safety import SafetyResult
from coachkg.skos import iri


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


# ---------- PROV-O JSON-LD (docs/provenance.md) ----------

PROV = "http://www.w3.org/ns/prov#"
CKG = "urn:coachkg:"
STAGES = ("read-request", "resolve", "safety-filter", "score", "select", "assemble")
_REF = {"@type": "@id"}
CONTEXT: dict[str, Any] = {
    "prov": PROV,
    "coachkg": CKG,
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "label": "rdfs:label",
    **{
        t: {"@id": f"prov:{t}", **_REF}
        for t in (
            "used",
            "wasGeneratedBy",
            "wasDerivedFrom",
            "wasInformedBy",
            "wasAssociatedWith",
            "wasAttributedTo",
            "hadMember",
        )
    },
    "startedAtTime": {"@id": "prov:startedAtTime", "@type": "xsd:dateTime"},
    "endedAtTime": {"@id": "prov:endedAtTime", "@type": "xsd:dateTime"},
    "generatedAtTime": {"@id": "prov:generatedAtTime", "@type": "xsd:dateTime"},
    **{
        t: {"@id": f"coachkg:{t}", **_REF}
        for t in (
            "exercise",
            "rule",
            "member",
            "from",
            "to",
            "region",
            "condition",
            "concept",
            "item",
            "awaitsConfirmationBy",
            "file",
        )
    },
    **{
        t: f"coachkg:{t}"
        for t in (
            "stage",
            "role",
            "status",
            "outcome",
            "reason",
            "trusted",
            "why",
            "countedAgainst",
            "score",
            "block",
            "position",
            "sets",
            "reps",
            "workSeconds",
            "restSeconds",
            "pickedBy",
            "flag",
            "edgeKind",
            "edgeRole",
            "edgeProv",
            "edgeSource",
            "said",
            "readAs",
            "readKind",
            "matchStatus",
            "method",
            "confidence",
            "side",
            "origin",
            "elapsedMs",
            "inputTokens",
            "outputTokens",
            "unverified",
            "note",
            "citation",
            "doi",
            "title",
        )
    },
}

AGENTS: dict[str, dict[str, Any]] = {
    "intent-model": {
        "@type": "prov:SoftwareAgent",
        "role": "intent",
        "label": "Request reader (language model; the model id is configuration, not recorded here)",
    },
    "selection-model": {
        "@type": "prov:SoftwareAgent",
        "role": "selection",
        "label": "Exercise orderer (language model; picks only from the safety-filtered pool)",
    },
    "resolver": {
        "@type": "prov:SoftwareAgent",
        "role": "resolver",
        "label": "Concept resolver (deterministic: exact and fuzzy label match)",
    },
    "safety-filter": {
        "@type": "prov:SoftwareAgent",
        "role": "safety-filter",
        "label": "Safety filter (deterministic graph traversal over dataset facts and signed rules)",
    },
    "scorer": {
        "@type": "prov:SoftwareAgent",
        "role": "scorer",
        "label": "Ranking (deterministic scoring rules)",
    },
    "assembler": {
        "@type": "prov:SoftwareAgent",
        "role": "assembler",
        "label": "Plan assembly (deterministic time budget and programming.yaml doses)",
    },
}


def agent_iri(name: str) -> str:
    return f"{CKG}agent/{name}"


def _condition_iri(c: str) -> str:
    return str(iri(c if ":" in c else f"condition:{c}"))


def edge_iri(e: dict[str, str]) -> str:
    """One IRI per graph edge: urn:coachkg:edge/<kind>/<src>/<dst>, node ids percent-encoded."""
    src, dst = (quote(e[k], safe="") for k in ("src", "dst"))
    return f"{CKG}edge/{e['kind']}/{src}/{dst}"


def prov_document(
    plan: dict[str, Any], safety: SafetyResult, rules: RuleSet, calls: list[CallStats]
) -> dict[str, Any]:
    """The whole run as PROV-O JSON-LD with an inline @context, so rdflib (or any JSON-LD
    processor) reads every exercise, reason, rule and exclusion as triples.

    Activities, one per stage: read-request -> resolve -> safety-filter -> score -> select ->
    assemble, chained by prov:wasInformedBy and by the entities each one used and generated.
    Model roles are agents by role name; model ids never appear here."""
    base = f"{CKG}plan/{plan['id']}"
    act = {s: f"{base}/activity/{s}" for s in STAGES}
    graph: list[dict[str, Any]] = []
    edges: dict[str, dict[str, Any]] = {}

    def edge(e: dict[str, str], prov: str | None = None, source: str | None = None) -> str:
        i = edge_iri(e)
        rec = edges.setdefault(
            i,
            {
                "@id": i,
                "@type": ["prov:Entity", "coachkg:Edge"],
                "edgeKind": e["kind"],
                "from": str(iri(e["src"])),
                "to": str(iri(e["dst"])),
            },
        )
        if prov and "edgeProv" not in rec:
            rec["edgeProv"] = prov
        if source and "edgeSource" not in rec:
            rec["edgeSource"] = source
        return i

    coach = f"{CKG}coach/{quote(str(plan.get('coach_id') or 'unknown'), safe='')}"
    member = str(iri(f"member:{plan['member_id']}"))
    graph.append({"@id": coach, "@type": ["prov:Agent", "prov:Person"], "role": "coach"})
    for name, a in AGENTS.items():
        graph.append({"@id": agent_iri(name), **a})

    movement = f"{CKG}graph/movement"
    request = f"{base}/request"
    intent = f"{base}/intent"
    candidates = f"{base}/candidates"
    selection = f"{base}/selection"
    programming = f"{CKG}file/{quote('kg/rules/programming.yaml', safe='')}"
    contra = f"{CKG}file/{quote('kg/rules/contraindications.yaml', safe='')}"
    graph += [
        {"@id": member, "@type": "prov:Entity", "label": "member record (synthetic)"},
        {"@id": movement, "@type": "prov:Entity", "label": "movement graph (KG1)"},
        {"@id": programming, "@type": "prov:Entity", "label": "kg/rules/programming.yaml"},
        {"@id": contra, "@type": "prov:Entity", "label": "kg/rules/contraindications.yaml"},
        {
            "@id": request,
            "@type": "prov:Entity",
            "label": "coach request (text is in the plan trace, not repeated here)",
            "wasAttributedTo": coach,
            "member": member,
        },
        {
            "@id": intent,
            "@type": "prov:Entity",
            "wasGeneratedBy": act["read-request"],
            "wasDerivedFrom": request,
        },
    ]

    # Readings: how each phrase was understood (resolver output).
    readings: list[str] = []
    for n, r in enumerate(plan["trace"]["read"]):
        i = f"{base}/reading/{n}"
        readings.append(i)
        graph.append(
            {
                "@id": i,
                "@type": ["prov:Entity", "coachkg:Reading"],
                "wasGeneratedBy": act["resolve"],
                "wasDerivedFrom": intent,
                "readKind": r["kind"],
                "said": r["said"],
                "readAs": r["understood_as"],
                "matchStatus": r["status"],
                "method": r["method"],
                "confidence": r["confidence"],
            }
        )

    # Safety filter: restrictions, rules and every decision with its evidence.
    restrictions: list[str] = []
    for n, rs in enumerate(safety.restrictions):
        i = f"{base}/restriction/{n}"
        restrictions.append(i)
        rec: dict[str, Any] = {
            "@id": i,
            "@type": ["prov:Entity", "coachkg:Restriction"],
            "wasGeneratedBy": act["safety-filter"],
            "region": [str(iri(x)) for x in sorted(rs.regions)],
            "origin": rs.origin,
            "confidence": round(rs.confidence, 2),
            "wasDerivedFrom": (
                [str(iri(f"member:{plan['member_id']}"))]
                if rs.origin.startswith("member-record")
                else readings
            ),
        }
        if rs.side:
            rec["side"] = rs.side
        if rs.condition:
            rec["condition"] = _condition_iri(rs.condition)
        graph.append(rec)
    by_rule = {r.id: r for r in rules.rules}
    used_rules: set[str] = set()
    decisions: list[str] = []
    for n, d in enumerate(safety.decisions):
        i = f"{base}/decision/{n}"
        decisions.append(i)
        derived = [
            edge({"src": ev["from"], "kind": ev["edge"], "dst": ev["to"]}, ev["prov"], ev["source"])
            for ev in d.evidence
        ]
        rec = {
            "@id": i,
            "@type": ["prov:Entity", "coachkg:SafetyDecision"],
            "wasGeneratedBy": act["safety-filter"],
            "exercise": str(iri(f"ex:{d.exercise_id}")),
            "outcome": d.outcome,
            "reason": d.reason,
            "trusted": d.trusted,
        }
        if d.rule:
            rid = f"{CKG}rule/{quote(d.rule, safe='')}"
            used_rules.add(d.rule)
            rec["rule"] = rid
            derived.append(rid)
        if d.reason.startswith("Loads the") and restrictions:
            derived += restrictions
        if not derived:
            derived = readings or [request]  # e.g. an exercise the request excluded by name
        rec["wasDerivedFrom"] = derived
        graph.append(rec)
    for rid in sorted(used_rules):
        rule = by_rule.get(rid)
        rec = {
            "@id": f"{CKG}rule/{quote(rid, safe='')}",
            "@type": ["prov:Entity", "coachkg:Rule"],
            "label": rule.paraphrase if rule else rid,
            "file": contra,
        }
        if rule:
            rec["condition"] = _condition_iri(rule.condition)
            rec["citation"] = [
                {"@id": f"https://doi.org/{c.doi}"} if c.doi else (c.short or c.dataset or "")
                for c in rule.citations
            ]
        graph.append(rec)
    excluded = {d.exercise_id for d in safety.decisions if d.outcome == "excluded"}
    graph.append(
        {
            "@id": candidates,
            "@type": ["prov:Entity", "prov:Collection", "coachkg:CandidateSet"],
            "wasGeneratedBy": act["safety-filter"],
            "hadMember": [str(iri(f"ex:{e.id}")) for e in safety.candidates],
            "note": f"{len(safety.candidates)} candidates, {len(excluded)} exercises excluded",
        }
    )

    # Score, select, assemble: one score entity per planned item, the selection, the items.
    items: list[str] = []
    scores: list[str] = []
    for b in plan["blocks"]:
        for n, it in enumerate(b["items"]):
            ex = str(iri(f"ex:{it['exercise_id']}"))
            score = f"{base}/score/{quote(it['exercise_id'], safe='')}"
            scores.append(score)
            graph.append(
                {
                    "@id": score,
                    "@type": ["prov:Entity", "coachkg:Ranking"],
                    "wasGeneratedBy": act["score"],
                    "wasDerivedFrom": candidates,
                    "exercise": ex,
                    "why": it["why"],
                    "countedAgainst": it["counted_against"],
                }
            )
            path = [edge(e) for e in it["path"]]
            for e in it["path"]:
                edges[edge_iri(e)]["edgeRole"] = e.get("role", "")
            item = f"{base}/item/{b['name']}/{n}"
            items.append(item)
            rec = {
                "@id": item,
                "@type": ["prov:Entity", "coachkg:PlanItem"],
                "wasGeneratedBy": act["assemble"],
                "wasDerivedFrom": [score, selection, *path],
                "exercise": ex,
                "label": it["name"],
                "block": b["name"],
                "position": n + 1,
                "sets": it["sets"],
                "restSeconds": it["rest_s"],
                "pickedBy": it["picked_by"],
                "why": it["why"],
            }
            if it.get("reps") is not None:
                rec["reps"] = it["reps"]
            if it.get("work_s") is not None:
                rec["workSeconds"] = it["work_s"]
            if it["flags"]:
                rec["flag"] = it["flags"]
            graph.append(rec)
    graph.append(
        {
            "@id": selection,
            "@type": ["prov:Entity", "coachkg:Selection"],
            "wasGeneratedBy": act["select"],
            "wasAttributedTo": agent_iri("selection-model"),
            "wasDerivedFrom": scores,
        }
    )
    graph.append(
        {
            "@id": base,
            "@type": ["prov:Entity", "prov:Collection", "coachkg:Plan"],
            "wasGeneratedBy": act["assemble"],
            "wasAttributedTo": agent_iri("assembler"),
            "wasDerivedFrom": [selection, candidates, request],
            "generatedAtTime": plan["created_at"],
            "title": plan["title"],
            "status": plan["status"],
            "awaitsConfirmationBy": coach,
            "member": member,
            "hadMember": items,
            "item": items,
            "unverified": plan["trace"]["unverified"],
            "note": plan["label"],
        }
    )

    # The activity chain.
    by_purpose = {c.purpose: c for c in calls}
    timings = plan.get("timings_ms", {})
    safety_started = next(
        (r.get("prov:startedAtTime") for r in safety.prov if r.get("@type") == "prov:Activity"), None
    )
    spec: dict[str, dict[str, Any]] = {
        "read-request": {
            "used": [request],
            "wasAssociatedWith": [coach, agent_iri("intent-model")],
            "call": "intent",
            "ms": timings.get("intent"),
        },
        "resolve": {"used": [intent, movement], "wasAssociatedWith": [agent_iri("resolver")]},
        "safety-filter": {
            "used": [
                *readings,
                member,
                movement,
                contra,
                *[f"{CKG}rule/{quote(r, safe='')}" for r in sorted(used_rules)],
            ],
            "wasAssociatedWith": [agent_iri("safety-filter")],
            "ms": timings.get("safety"),
        },
        "score": {"used": [candidates, member], "wasAssociatedWith": [agent_iri("scorer")]},
        "select": {
            "used": scores,
            "wasAssociatedWith": [agent_iri("selection-model")],
            "call": "selection",
            "ms": timings.get("selection"),
        },
        "assemble": {
            "used": [selection, programming],
            "wasAssociatedWith": [agent_iri("assembler")],
        },
    }
    prev: str | None = None
    for stage in STAGES:
        sp = spec[stage]
        rec = {
            "@id": act[stage],
            "@type": "prov:Activity",
            "stage": stage,
            "used": [u for u in sp["used"] if u] or [request],
            "wasAssociatedWith": sp["wasAssociatedWith"],
        }
        if prev:
            rec["wasInformedBy"] = prev
        if stage == "safety-filter" and safety_started:
            rec["startedAtTime"] = safety_started
        if sp.get("ms") is not None:
            rec["elapsedMs"] = sp["ms"]
        c = by_purpose.get(sp.get("call", ""))
        if c:
            rec["inputTokens"] = c.input_tokens
            rec["outputTokens"] = c.output_tokens
        graph.append(rec)
        prev = act[stage]
    graph += edges.values()
    return {"@context": CONTEXT, "@graph": graph}

"""Deterministic safety filter over the movement graph, with provenance records.

Policy (docs/rules.md):
- Facts that would ALLOW an exercise must come from the dataset or a human-signed rule file.
- Facts from unsigned (model-attributed) rule files may only make the filter MORE restrictive,
  and every time one is used the plan is marked "unverified" with the reason.
- Injury mentions fail closed: an unresolved mention blocks drafting and asks the coach; an
  ambiguous one restricts every candidate region.
- Member text never removes a restriction. Only a coach clearance (structured field) relaxes
  knee loading, and only for exercises whose attributes come from a signed file.

The filter emits PROV-O style records (prov:Activity for the run, prov:Entity per decision) as it
runs. Nothing downstream may add reasons the filter did not record.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from coachkg.data import Exercise
from coachkg.kg.graph import Edge, NetworkXStore, ex_node, is_trusted, region_node
from coachkg.kg.rules import ContraRule, RuleSet
from coachkg.member import Clearance, Member
from coachkg.resolver import BodyMention, Resolver

Side = Literal["left", "right", "both"]
_BEND = {
    "none": "no loaded knee bend",
    "shallow": "shallow knee bend, up to about 45°",
    "deep": "deep knee bend",
}
# Regions too broad to count as "the same place" as an injury (every limb exercise would match).
_TOO_BROAD = {region_node("body")}


@dataclass(frozen=True)
class Restriction:
    id: str
    regions: frozenset[str]
    side: Side | None
    condition: str | None
    origin: str  # member-record:<injury id> | request | coach-confirmed
    confidence: float
    injury_id: str | None = None


@dataclass
class Decision:
    exercise_id: str
    name: str
    outcome: Literal["excluded", "downranked", "flagged"]
    reason: str
    rule: str | None
    evidence: list[dict[str, str]]
    trusted: bool  # False when it rests on an unsigned rule (restrictive use only)


@dataclass
class Blocker:
    """Drafting stops until the coach answers this."""

    mention: str
    reason: str
    candidates: list[dict[str, Any]]


@dataclass
class SafetyRequest:
    member: Member
    injury_mentions: list[BodyMention] = field(default_factory=list)
    exclude_concepts: list[str] = field(default_factory=list)  # family:* or ex:* node ids
    unavailable_equipment: list[str] = field(default_factory=list)  # equipment:* removed by request
    clearances: list[Clearance] = field(default_factory=list)
    confirmed_regions: list[tuple[str, Side | None]] = field(default_factory=list)  # coach answers


@dataclass
class SafetyResult:
    candidates: list[Exercise]
    decisions: list[Decision]
    blockers: list[Blocker]
    restrictions: list[Restriction]
    unverified: list[str]
    prov: list[dict[str, Any]]

    @property
    def blocked(self) -> bool:
        return bool(self.blockers)

    def flags_for(self, exercise_id: str) -> list[Decision]:
        return [d for d in self.decisions if d.exercise_id == exercise_id and d.outcome != "excluded"]


class SafetyFilter:
    def __init__(self, store: NetworkXStore, rules: RuleSet, resolver: Resolver) -> None:
        self.store = store
        self.rules = rules
        self.resolver = resolver
        self.joint_regions = {
            region_node(r.id) for r in rules.regions if r.dataset_joint
        }  # regions the dataset loads directly

    # ---------- anatomy ----------
    def _related(self, region: str) -> tuple[set[str], bool]:
        """Region plus its part-of ancestors and descendants. Returns (regions, used_untrusted)."""
        out, untrusted = {region}, False
        stack = [region]
        while stack:  # descendants
            n = stack.pop()
            for e in self.store.in_edges(n, "part-of"):
                untrusted |= not is_trusted(e.prov)
                if e.src not in out:
                    out.add(e.src)
                    stack.append(e.src)
        n = region
        while True:  # ancestors
            ups = self.store.out_edges(n, "part-of")
            if not ups:
                break
            untrusted |= not is_trusted(ups[0].prov)
            n = ups[0].dst
            if n not in _TOO_BROAD:
                out.add(n)
        return out, untrusted

    def _trusted_link(self, region: str) -> bool:
        """Can this region be tied to a dataset joint using only trusted edges?"""
        if region in self.joint_regions:
            return True
        related = {region}
        stack = [region]
        while stack:
            n = stack.pop()
            for e in self.store.in_edges(n, "part-of", trusted_only=True) + self.store.out_edges(
                n, "part-of", trusted_only=True
            ):
                other = e.src if e.dst == n else e.dst
                if other not in related and other not in _TOO_BROAD:
                    related.add(other)
                    stack.append(other)
        return bool(related & self.joint_regions)

    # ---------- restrictions ----------
    def _region_for_injury_record(self, joint: str | None, region_text: str) -> str | None:
        if joint:
            for r in self.rules.regions:
                if r.dataset_joint == joint:
                    return region_node(r.id)
        m = self.resolver.parse_body_mention(region_text)
        if m.resolution.status == "accepted" and m.resolution.concept:
            return m.resolution.concept if m.resolution.concept.startswith("region:") else None
        return None

    def region_for_injury(self, joint: str | None, region_text: str) -> str | None:
        return self._region_for_injury_record(joint, region_text)

    def _condition_regions(self, condition: str) -> list[str]:
        return [e.dst for e in self.store.out_edges(condition, "affects")]

    def build_restrictions(
        self, req: SafetyRequest, blockers: list[Blocker], unverified: list[str]
    ) -> list[Restriction]:
        out: list[Restriction] = []
        # 1. The member record (dataset): every injury that is not resolved.
        for inj in req.member.injuries:
            if not inj.active:
                continue
            region = self._region_for_injury_record(inj.joint, inj.region)
            side = self.resolver.parse_body_mention(inj.region).side
            condition = None
            for m in self.resolver.find_body_mentions(inj.notes or ""):
                if m.resolution.concept and m.resolution.concept.startswith("condition:"):
                    condition = m.resolution.concept
            if region is None:
                blockers.append(
                    Blocker(
                        inj.region, "The injury on the member record doesn't match a known body region.", []
                    )
                )
                continue
            out.append(
                Restriction(
                    f"r-{inj.id}",
                    frozenset({region}),
                    side,
                    condition,
                    f"member-record:{inj.id}",
                    1.0,
                    inj.id,
                )
            )
        # 2. Coach-confirmed regions (answers to an earlier blocker).
        for i, (region, side) in enumerate(req.confirmed_regions):
            out.append(
                Restriction(f"r-confirmed-{i}", frozenset({region}), side, None, "coach-confirmed", 1.0)
            )
        # 3. Injury mentions in the request: fail closed.
        for i, m in enumerate(req.injury_mentions):
            res = m.resolution
            if res.status == "accepted" and res.concept:
                regions: set[str] = set()
                condition = None
                if res.concept.startswith("condition:"):
                    condition = res.concept
                    regions = set(self._condition_regions(res.concept))
                else:
                    regions = {res.concept}
                if regions and not all(self._trusted_link(r) for r in regions):
                    blockers.append(
                        Blocker(
                            m.text,
                            "This body region can't be tied to the exercise data through signed anatomy "
                            "rules. Confirm which joint to protect.",
                            [{"concept": r, "label": self.store.node(r)["label"]} for r in sorted(regions)],
                        )
                    )
                    continue
                if not regions:
                    blockers.append(Blocker(m.text, "The request mentions pain without a body region.", []))
                    continue
                out.append(
                    Restriction(f"r-request-{i}", frozenset(regions), m.side, condition, "request", res.score)
                )
            elif res.status == "ambiguous":
                regions = set()
                for c in res.candidates:
                    regions |= (
                        {c.concept}
                        if c.concept.startswith("region:")
                        else set(self._condition_regions(c.concept))
                    )
                usable = {r for r in regions if self._trusted_link(r)}
                if not usable:
                    blockers.append(
                        Blocker(
                            m.text,
                            "The body region in the request is unclear.",
                            [
                                {"concept": c.concept, "label": c.label, "score": round(c.score, 2)}
                                for c in res.candidates
                            ],
                        )
                    )
                    continue
                unverified.append(f'"{m.text}" was ambiguous; every candidate region is restricted.')
                out.append(
                    Restriction(f"r-request-{i}", frozenset(usable), m.side, None, "request", res.score)
                )
            else:
                blockers.append(
                    Blocker(
                        m.text,
                        "The request mentions an injury or pain that doesn't match a body region.",
                        [
                            {"concept": c.concept, "label": c.label, "score": round(c.score, 2)}
                            for c in res.candidates
                        ],
                    )
                )
        # A request that repeats an injury already restricted adds nothing; keep one restriction.
        kept: list[Restriction] = []
        for r in out:
            if r.origin == "request" and any(self._covers(k, r) for k in kept):
                continue
            kept.append(r)
        return kept

    @staticmethod
    def _covers(a: Restriction, b: Restriction) -> bool:
        side_ok = a.side in (None, "both") or a.side == b.side
        cond_ok = b.condition is None or b.condition == a.condition
        return b.regions <= a.regions and side_ok and cond_ok and a.confidence >= b.confidence

    # ---------- rule evaluation ----------
    def _attributes(self, ex_id: str) -> tuple[Any, bool]:
        d = self.store.node(ex_node(ex_id))
        attrs = d.get("attributes")
        return attrs, attrs is not None and is_trusted(d.get("attributes_prov", "model"))

    def _rule_hits(self, rule: ContraRule, ex: Exercise, attrs: Any) -> bool:
        w = rule.when
        if w.patterns_any and set(w.patterns_any) & set(ex.movement_patterns):
            return True
        if attrs is None:
            return False
        if w.loaded_knee_flexion and attrs.loaded_knee_flexion in w.loaded_knee_flexion:
            return True
        if w.impact and attrs.impact in w.impact:
            return True
        return bool(w.kneeling and attrs.kneeling)

    def _rule_usable(self, rule: ContraRule) -> bool:
        return self.rules.contra_review.trusted and rule.sourced

    @staticmethod
    def _side_conflicts(restriction_side: Side | None, exercise_side: str) -> bool:
        if restriction_side is None or restriction_side == "both" or exercise_side == "both":
            return True
        return restriction_side == exercise_side

    # ---------- main ----------
    def run(self, req: SafetyRequest) -> SafetyResult:
        started = datetime.now(UTC).isoformat(timespec="milliseconds")
        blockers: list[Blocker] = []
        unverified: list[str] = []
        restrictions = self.build_restrictions(req, blockers, unverified)
        decisions: list[Decision] = []
        candidates: list[Exercise] = []
        clear_by_injury = {c.injury_id: c for c in req.clearances if c.cleared_low_impact}

        owned = {f"equipment:{q.strip().lower()}" for q in req.member.equipment_available}
        owned -= set(req.unavailable_equipment)
        excluded_families = self._expand_exclusions(req.exclude_concepts)

        for node in self.store.nodes("exercise"):
            d = self.store.node(node)
            ex: Exercise = d["exercise"]
            if ex.origin == "authored" and not is_trusted(d["prov"]):
                # Their joint loads are unsigned, so the filter can't vouch for them.
                continue
            reasons: list[Decision] = []

            # Equipment (dataset or signed authored edges).
            missing = [e for e in self.store.out_edges(node, "requires") if e.dst not in owned]
            if missing:
                labels = ", ".join(self.store.node(e.dst)["label"] for e in missing)
                reasons.append(self._dec(ex, "excluded", f"Needs {labels}", None, missing))

            # Exclusions in the request (families or named exercises).
            hit = self._exclusion_hit(node, excluded_families)
            if hit:
                fam_label, edges = hit
                reasons.append(self._dec(ex, "excluded", f"Excluded by request ({fam_label})", None, edges))

            attrs, attrs_trusted = self._attributes(ex.id)
            for r in restrictions:
                stress_hits = []
                for e in self.store.out_edges(node, "stresses"):
                    if not self._side_conflicts(r.side, e.attrs.get("laterality", "both")):
                        continue
                    for reg in r.regions:
                        related, untrusted_anatomy = self._related(reg)
                        if e.dst in related:
                            stress_hits.append((e, untrusted_anatomy))
                if stress_hits:
                    e, untrusted_anatomy = stress_hits[0]
                    cleared = r.injury_id is not None and r.injury_id in clear_by_injury
                    region_label = self.store.node(e.dst)["label"]
                    where = f"{r.side + ' ' if r.side and r.side != 'both' else ''}{region_label.lower()}"
                    if (
                        cleared
                        and attrs_trusted
                        and attrs.impact != "high"
                        and attrs.loaded_knee_flexion != "deep"
                    ):
                        reasons.append(
                            self._dec(
                                ex,
                                "downranked",
                                f"Loads the {where} ({_BEND[attrs.loaded_knee_flexion]}); "
                                "coach cleared low-impact loading",
                                None,
                                [e],
                            )
                        )
                    else:
                        why = f"Loads the {where} ({r.origin.split(':')[0].replace('-', ' ')})"
                        if cleared and not attrs_trusted:
                            why += "; clearance needs signed exercise attributes"
                        dec = self._dec(ex, "excluded", why, None, [e])
                        if untrusted_anatomy or not is_trusted(e.prov):
                            dec.trusted = False
                        reasons.append(dec)
                # Condition rules apply to every exercise (e.g. plyometrics with knee pain).
                if r.condition:
                    for rule in self.rules.rules:
                        if f"condition:{rule.condition}" != r.condition or not self._rule_hits(
                            rule, ex, attrs
                        ):
                            continue
                        outcome: Literal["excluded", "flagged"] = (
                            "excluded" if rule.effect == "exclude" else "flagged"
                        )
                        dec = self._dec(ex, outcome, rule.paraphrase, rule.id, [])
                        by_pattern = bool(set(rule.when.patterns_any or []) & set(ex.movement_patterns))
                        facts_trusted = (by_pattern and ex.origin == "dataset") or attrs_trusted
                        dec.trusted = self._rule_usable(rule) and facts_trusted
                        reasons.append(dec)

            decisions.extend(reasons)
            if not any(x.outcome == "excluded" for x in reasons):
                candidates.append(ex)

        rules_by_id = {r.id: r for r in self.rules.rules}
        for dcs in decisions:
            if dcs.trusted:
                continue
            dcs_rule = rules_by_id.get(dcs.rule or "")
            why = (
                "rule has no checked source"
                if dcs_rule and self.rules.contra_review.trusted and not dcs_rule.sourced
                else "rests on an unsigned rule"
            )
            unverified.append(f"{dcs.name}: {dcs.reason} ({why})")
        for label, _review in self._unsigned_files():
            unverified.append(f"{label} is not signed yet, so the filter cannot use it to allow anything.")

        prov = self._prov(started, req, restrictions, decisions, blockers)
        return SafetyResult(candidates, decisions, blockers, restrictions, sorted(set(unverified)), prov)

    # ---------- helpers ----------
    def _dec(
        self,
        ex: Exercise,
        outcome: Literal["excluded", "downranked", "flagged"],
        reason: str,
        rule: str | None,
        edges: Iterable[Edge],
    ) -> Decision:
        ev = [{"edge": e.kind, "from": e.src, "to": e.dst, "prov": e.prov, "source": e.source} for e in edges]
        return Decision(ex.id, ex.name, outcome, reason, rule, ev, all(is_trusted(e["prov"]) for e in ev))

    def _expand_exclusions(self, concepts: list[str]) -> dict[str, str]:
        """family/exercise node -> label of the requested concept that excludes it (is-a descendants)."""
        out: dict[str, str] = {}
        for c in concepts:
            label = self.store.node(c)["label"]
            out[c] = label
            if c.startswith("family:"):
                stack = [c]
                while stack:
                    n = stack.pop()
                    for e in self.store.in_edges(n, "is-a"):
                        if e.src not in out:
                            out[e.src] = label
                            stack.append(e.src)
        return out

    def _exclusion_hit(self, node: str, excluded: dict[str, str]) -> tuple[str, list[Edge]] | None:
        if node in excluded:
            return excluded[node], []
        for e in self.store.out_edges(node, "variant-of"):
            if e.dst in excluded:
                return excluded[e.dst], [e]
        return None

    def _unsigned_files(self) -> list[tuple[str, Any]]:
        r = self.rules
        pairs = [
            ("kg/rules/anatomy.yaml", r.anatomy_review),
            ("kg/rules/exercise_attributes.yaml", r.attributes_review),
            ("kg/rules/contraindications.yaml", r.contra_review),
            ("kg/rules/families.yaml", r.families_review),
            ("kg/authored/exercises.yaml", r.authored_review),
        ]
        return [(label, rev) for label, rev in pairs if not rev.trusted]

    def _prov(
        self,
        started: str,
        req: SafetyRequest,
        restrictions: list[Restriction],
        decisions: list[Decision],
        blockers: list[Blocker],
    ) -> list[dict[str, Any]]:
        act = "urn:coachkg:activity:safety-filter"
        records: list[dict[str, Any]] = [
            {
                "@id": act,
                "@type": "prov:Activity",
                "prov:startedAtTime": started,
                "prov:endedAtTime": datetime.now(UTC).isoformat(timespec="milliseconds"),
                "prov:used": [f"urn:coachkg:member:{req.member.id}", "urn:coachkg:graph:movement"]
                + [f"urn:coachkg:rules:{label}" for label, _ in self._unsigned_files()],
            }
        ]
        for m in req.injury_mentions:
            records.append(
                {
                    "@type": "prov:Entity",
                    "kind": "resolution",
                    "prov:wasGeneratedBy": act,
                    "mention": m.text,
                    "side": m.side,
                    **m.resolution.as_trace(),
                }
            )
        for r in restrictions:
            records.append(
                {
                    "@type": "prov:Entity",
                    "kind": "restriction",
                    "prov:wasGeneratedBy": act,
                    "regions": sorted(r.regions),
                    "side": r.side,
                    "condition": r.condition,
                    "prov:wasDerivedFrom": r.origin,
                    "confidence": round(r.confidence, 2),
                }
            )
        for d in decisions:
            records.append(
                {
                    "@type": "prov:Entity",
                    "kind": "decision",
                    "prov:wasGeneratedBy": act,
                    "exercise": ex_node(d.exercise_id),
                    "outcome": d.outcome,
                    "reason": d.reason,
                    "rule": d.rule,
                    "evidence": d.evidence,
                    "trusted": d.trusted,
                }
            )
        for b in blockers:
            records.append(
                {
                    "@type": "prov:Entity",
                    "kind": "blocker",
                    "prov:wasGeneratedBy": act,
                    "mention": b.mention,
                    "reason": b.reason,
                }
            )
        return records

"""Load and validate the authored rule files in kg/rules/ and kg/authored/.

Attribution decides what the safety filter may use. A file is attributed to ``model`` while it is a
draft and to ``human:<initials>`` once a reviewer signs it (review.status: signed, reviewer set).
Unsigned files still load, so the UI can show what is pending, but the safety filter ignores them.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from coachkg.data import Exercise


class Review(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: Literal["draft", "signed"] = "draft"
    drafted_by: str = "model"
    reviewer: str | None = None
    signed_on: date | None = None

    @model_validator(mode="after")
    def _signed_needs_reviewer(self) -> Review:
        if self.status == "signed" and not (self.reviewer and self.signed_on):
            raise ValueError("a signed rule file needs reviewer initials and signed_on")
        return self

    @property
    def attributed_to(self) -> str:
        return f"human:{self.reviewer}" if self.status == "signed" else "model"

    @property
    def trusted(self) -> bool:
        """Only human-signed files may drive safety decisions."""
        return self.status == "signed"


class Region(BaseModel):
    id: str
    label: str
    alt_labels: list[str] = Field(default_factory=list)
    part_of: str | None = None
    sided: bool = False
    dataset_joint: str | None = None


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doi: str | None = None
    short: str | None = None
    dataset: str | None = None
    doi_checked: date | None = None
    claim_checked: str | None = None

    @property
    def checked(self) -> bool:
        """A dataset field is its own evidence; a paper needs both its DOI and its claim checked."""
        if self.dataset:
            return True
        return bool(self.doi and self.doi_checked and self.claim_checked)


class Condition(BaseModel):
    id: str
    label: str
    alt_labels: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)


class RuleWhen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loaded_knee_flexion: list[Literal["none", "shallow", "deep"]] | None = None
    impact: list[Literal["none", "low", "high"]] | None = None
    patterns_any: list[str] | None = None
    kneeling: bool | None = None


class ContraRule(BaseModel):
    id: str
    condition: str
    when: RuleWhen
    effect: Literal["exclude", "flag"]
    paraphrase: str
    citations: list[Citation] = Field(default_factory=list)

    @property
    def sourced(self) -> bool:
        return any(c.checked for c in self.citations)

    def hits(self, patterns: list[str], attrs: Any) -> bool:
        """Does an exercise with these movement patterns and attributes fall under this rule?"""
        w = self.when
        if w.patterns_any and set(w.patterns_any) & set(patterns):
            return True
        if attrs is None:
            return False
        if w.loaded_knee_flexion and attrs.loaded_knee_flexion in w.loaded_knee_flexion:
            return True
        if w.impact and attrs.impact in w.impact:
            return True
        return bool(w.kneeling and attrs.kneeling)


class ExerciseAttributes(BaseModel):
    model_config = ConfigDict(extra="forbid")

    loaded_knee_flexion: Literal["none", "shallow", "deep"]
    impact: Literal["none", "low", "high"]
    kneeling: bool = False
    extra_stresses: list[str] = Field(default_factory=list)


class Family(BaseModel):
    id: str
    label: str
    alt_labels: list[str] = Field(default_factory=list)
    is_a: str | None = None
    members: list[str] = Field(default_factory=list)


class Substitute(BaseModel):
    missing: str
    use: str
    patterns: list[str]
    caveat: str | None = None


class RuleSet(BaseModel):
    """Everything under kg/, validated and cross-checked against the exercise catalog."""

    anatomy_review: Review
    regions: list[Region]
    attributes_review: Review
    attributes: dict[str, ExerciseAttributes]
    contra_review: Review
    conditions: list[Condition]
    rules: list[ContraRule]
    families_review: Review
    families: list[Family]
    equipment_review: Review
    substitutes: list[Substitute]
    authored_review: Review
    authored: list[Exercise]


def _read(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a YAML mapping")
    return data


def load_rules(kg_dir: Path, catalog: list[Exercise]) -> RuleSet:
    rules_dir = kg_dir / "rules"
    anatomy = _read(rules_dir / "anatomy.yaml")
    attrs = _read(rules_dir / "exercise_attributes.yaml")
    contra = _read(rules_dir / "contraindications.yaml")
    fams = _read(rules_dir / "families.yaml")
    equip = _read(rules_dir / "equipment.yaml")
    authored_raw = _read(kg_dir / "authored" / "exercises.yaml")

    authored = [
        Exercise.model_validate({k: v for k, v in row.items() if k != "alt_labels"} | {"origin": "authored"})
        for row in authored_raw["exercises"]
    ]
    rs = RuleSet(
        anatomy_review=Review.model_validate(anatomy["review"]),
        regions=[Region.model_validate(r) for r in anatomy["regions"]],
        attributes_review=Review.model_validate(attrs["review"]),
        attributes={k: ExerciseAttributes.model_validate(v) for k, v in attrs["exercises"].items()},
        contra_review=Review.model_validate(contra["review"]),
        conditions=[Condition.model_validate(c) for c in contra["conditions"]],
        rules=[ContraRule.model_validate(r) for r in contra["rules"]],
        families_review=Review.model_validate(fams["review"]),
        families=[Family.model_validate(f) for f in fams["families"]],
        equipment_review=Review.model_validate(equip["review"]),
        substitutes=[Substitute.model_validate(s) for s in equip["substitutes"]],
        authored_review=Review.model_validate(authored_raw["review"]),
        authored=authored,
    )
    _cross_check(rs, catalog)
    return rs


def authored_alt_labels(kg_dir: Path) -> dict[str, list[str]]:
    raw = _read(kg_dir / "authored" / "exercises.yaml")
    return {row["name"]: list(row.get("alt_labels", [])) for row in raw["exercises"]}


def _cross_check(rs: RuleSet, catalog: list[Exercise]) -> None:
    """Fail loudly on references to things that do not exist. Rules must never point at nothing."""
    names = {e.name for e in catalog} | {e.name for e in rs.authored}
    if len(names) != len(catalog) + len(rs.authored):
        raise ValueError("authored exercise names must not collide with catalog names")
    region_ids = {r.id for r in rs.regions}
    for r in rs.regions:
        if r.part_of and r.part_of not in region_ids:
            raise ValueError(f"region {r.id}: unknown part_of {r.part_of}")
    dataset_joints = {j for e in catalog for j in e.joints_loaded}
    mapped = {r.dataset_joint for r in rs.regions if r.dataset_joint}
    if missing := dataset_joints - mapped:
        raise ValueError(f"dataset joints without a region: {sorted(missing)}")
    for name, a in rs.attributes.items():
        if name not in names:
            raise ValueError(f"exercise_attributes: unknown exercise {name!r}")
        for reg in a.extra_stresses:
            if reg not in region_ids:
                raise ValueError(f"exercise_attributes {name!r}: unknown region {reg}")
    cond_ids = {c.id for c in rs.conditions}
    for c in rs.conditions:
        for reg in c.regions:
            if reg not in region_ids:
                raise ValueError(f"condition {c.id}: unknown region {reg}")
    patterns = {p for e in catalog for p in e.movement_patterns} | {
        p for e in rs.authored for p in e.movement_patterns
    }
    for rule in rs.rules:
        if rule.condition not in cond_ids:
            raise ValueError(f"rule {rule.id}: unknown condition {rule.condition}")
        for p in rule.when.patterns_any or []:
            if p not in patterns:
                raise ValueError(f"rule {rule.id}: unknown pattern {p!r}")
    fam_ids = {f.id for f in rs.families}
    for f in rs.families:
        if f.is_a and f.is_a not in fam_ids:
            raise ValueError(f"family {f.id}: unknown is_a {f.is_a}")
        for m in f.members:
            if m not in names:
                raise ValueError(f"family {f.id}: unknown member {m!r}")
    equipment = {q for e in catalog for q in e.equipment_required} | {
        q for e in rs.authored for q in e.equipment_required
    }
    for s in rs.substitutes:
        for q in (s.missing, s.use):
            if q not in equipment:
                raise ValueError(f"substitute: unknown equipment {q!r}")
        for p in s.patterns:
            if p not in patterns:
                raise ValueError(f"substitute {s.missing}->{s.use}: unknown pattern {p!r}")

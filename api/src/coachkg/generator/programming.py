"""Programming defaults (kg/rules/programming.yaml): doses, block shares and focus patterns."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from coachkg.kg.rules import Review


class Dose(BaseModel):
    sets: int
    reps: int | None = None
    work_s: int | None = None
    rest_s: int = 0


class EdgeBlock(BaseModel):
    share: float
    min_minutes: float
    max_minutes: float
    patterns: list[str]
    dose: Dose


class MainBlock(BaseModel):
    dose_reps: Dose
    dose_duration: Dose
    min_sets: int


class Blocks(BaseModel):
    warmup: EdgeBlock
    main: MainBlock
    cooldown: EdgeBlock


class Programming(BaseModel):
    review: Review
    tempo_s: float
    transition_s: float
    blocks: Blocks
    focus_patterns: dict[str, list[str]]


def load_programming(kg_dir: Path) -> Programming:
    return Programming.model_validate(yaml.safe_load((kg_dir / "rules" / "programming.yaml").read_text()))

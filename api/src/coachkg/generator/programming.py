"""Programming defaults (kg/rules/programming.yaml): doses, block shares and focus patterns."""

from __future__ import annotations

from datetime import date
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


class FallingAdherence(BaseModel):
    weeks: int
    drop_points: int


class Journey(BaseModel):
    new_member_days: int
    falling_adherence: FallingAdherence
    main_sets: int


class Programming(BaseModel):
    review: Review
    tempo_s: float
    transition_s: float
    blocks: Blocks
    focus_patterns: dict[str, list[str]]
    journey: Journey | None = None

    def lighter(self) -> Programming:
        """The same programming with the journey-stage main sets."""
        if self.journey is None:
            return self
        sets = self.journey.main_sets
        main = self.blocks.main.model_copy(
            update={
                "dose_reps": self.blocks.main.dose_reps.model_copy(update={"sets": sets}),
                "dose_duration": self.blocks.main.dose_duration.model_copy(update={"sets": sets}),
                "min_sets": min(self.blocks.main.min_sets, sets),
            }
        )
        return self.model_copy(update={"blocks": self.blocks.model_copy(update={"main": main})})


def journey_reason(prog: Programming, member_since: str | None, weekly: list[int], as_of: date) -> str | None:
    """Why this member gets the lighter main block, or None. Reads dates and completion numbers only."""
    j = prog.journey
    if j is None:
        return None
    if member_since:
        try:
            days = (as_of - date.fromisoformat(member_since)).days
        except ValueError:
            days = None
        if days is not None and 0 <= days <= j.new_member_days:
            return f"member joined {days} days ago"
    recent = weekly[-j.falling_adherence.weeks :]
    if len(recent) >= 2 and recent[0] - recent[-1] >= j.falling_adherence.drop_points:
        return f"weekly completion fell from {recent[0]}% to {recent[-1]}% over the last {len(recent)} weeks"
    return None


def load_programming(kg_dir: Path) -> Programming:
    return Programming.model_validate(yaml.safe_load((kg_dir / "rules" / "programming.yaml").read_text()))

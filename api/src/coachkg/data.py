"""Typed views of the two input files. Fields the files may omit are optional, never invented."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Exercise(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    muscle_groups: list[str]
    joints_loaded: list[str]
    movement_patterns: list[str]
    equipment_required: list[str]
    is_bilateral: bool
    side: str | None
    priority_tier: int | None = None
    is_reps: bool | None = None
    is_duration: bool | None = None
    supports_weight: bool | None = None
    estimated_rep_duration: float | None = None
    bilateral_pair_id: str | None = None
    # "dataset" for rows from exercises.json, "authored" for exercises we wrote in kg/authored/.
    origin: Literal["dataset", "authored"] = "dataset"

    @property
    def laterality(self) -> Literal["left", "right", "both"]:
        """Which side of the body the exercise loads. Rows with no side load both sides."""
        if self.side is None:
            return "both"
        if self.side.startswith("left"):
            return "left"
        if self.side.startswith("right"):
            return "right"
        return "both"


def load_exercises(data_dir: Path) -> list[Exercise]:
    raw = json.loads((data_dir / "exercises.json").read_text())
    return [Exercise.model_validate(row) for row in raw]


def load_member_raw(data_dir: Path) -> dict[str, object]:
    data: dict[str, object] = json.loads((data_dir / "member-context.json").read_text())
    return data

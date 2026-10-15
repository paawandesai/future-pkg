"""Member context (KG 2) views used by the safety filter and the copilot.

Member-authored text (chat) is untrusted: it is carried as quoted data with ``member-said``
provenance and can never lift a restriction. Only the coach, through a structured field, can.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Injury(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    region: str
    joint: str | None = None
    status: str
    severity: str | None = None
    since: date | None = None
    notes: str | None = None

    @property
    def active(self) -> bool:
        return self.status.lower() not in {"resolved", "healed", "cleared"}


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ts: str | None = None
    sender: Literal["member", "coach"] | str = Field(alias="from")
    text: str
    attachments: list[dict[str, Any]] | None = None

    @property
    def provenance(self) -> str:
        return "member-said" if self.sender == "member" else "coach-said"


class Member(BaseModel):
    """The fields the dashboard uses. Unknown keys are ignored, missing ones stay None."""

    model_config = ConfigDict(extra="ignore")

    profile: dict[str, Any]
    goals: list[dict[str, Any]] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)
    equipment_available: list[str] = Field(default_factory=list)
    injuries: list[Injury] = Field(default_factory=list)
    workout_history: list[dict[str, Any]] = Field(default_factory=list)
    adherence: dict[str, Any] | None = None
    biomarkers: dict[str, Any] | None = None
    labs: dict[str, Any] | None = None
    chat_history: list[ChatMessage] = Field(default_factory=list)
    coach_brief: dict[str, Any] | None = None

    @property
    def id(self) -> str:
        return str(self.profile["id"])

    @property
    def name(self) -> str:
        return str(self.profile.get("name", ""))


class Clearance(BaseModel):
    """A coach's structured clearance for one injury. Never derived from chat or request text."""

    injury_id: str
    cleared_low_impact: bool
    by: str
    at: str


def load_member(data_dir: Path, filename: str = "member-context.json") -> Member:
    return Member.model_validate(json.loads((data_dir / filename).read_text()))

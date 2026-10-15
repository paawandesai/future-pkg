"""Who is calling. Mock mode is for local runs only; any other mode without a verifier fails closed."""

from __future__ import annotations

import os

from fastapi import HTTPException

from coachkg.config import load_settings


def current_coach() -> str:
    mode = load_settings().auth_mode
    if mode == "mock":
        return os.environ.get("DEMO_COACH_ID", "coach_01HXSAM")
    raise HTTPException(status_code=401, detail="Sign in required")

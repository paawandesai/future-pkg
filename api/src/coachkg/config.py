"""Runtime configuration, read from the environment. Secrets are read by name and never logged."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    kg_dir: Path
    fixtures_dir: Path
    as_of_date: date
    auth_mode: str
    llm_model_fast: str | None
    llm_model_main: str | None

    @property
    def llm_configured(self) -> bool:
        has_key = os.environ.get("ANTHROPIC_FUTURE_API_KEY") or os.environ.get("ANTHROPIC_SECRET_ID")
        return bool(has_key) and bool(self.llm_model_main)


def load_settings() -> Settings:
    return Settings(
        data_dir=Path(os.environ.get("DATA_DIR", REPO_ROOT / "data")),
        kg_dir=Path(os.environ.get("KG_DIR", REPO_ROOT / "kg")),
        fixtures_dir=Path(os.environ.get("FIXTURES_DIR", REPO_ROOT / "fixtures")),
        as_of_date=date.fromisoformat(os.environ.get("AS_OF_DATE", "2026-06-04")),
        auth_mode=os.environ.get("AUTH_MODE", "mock"),
        llm_model_fast=os.environ.get("LLM_MODEL_FAST") or None,
        llm_model_main=os.environ.get("LLM_MODEL_MAIN") or None,
    )


def anthropic_api_key() -> str | None:
    """The key from the environment locally, or from Secrets Manager when deployed.

    The deployed function gets only the secret's id (ANTHROPIC_SECRET_ID); the value never
    appears in IaC, stack outputs or the function's configuration.
    """
    key = os.environ.get("ANTHROPIC_FUTURE_API_KEY")
    if key:
        return key
    secret_id = os.environ.get("ANTHROPIC_SECRET_ID")
    return _secret_value(secret_id) if secret_id else None


@lru_cache(maxsize=4)
def _secret_value(secret_id: str) -> str:
    import boto3  # type: ignore[import-not-found]  # provided by the Lambda runtime; not a local dependency

    value: str = boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)["SecretString"]
    return value

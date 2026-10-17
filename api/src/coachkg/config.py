"""Runtime configuration, read from the environment. Secrets are read by name and never logged."""

from __future__ import annotations

import json
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
        has_key = any(os.environ.get(v) for v in (*KEY_VARS, "ANTHROPIC_SECRET_ID"))
        return bool(has_key) and bool(self.llm_model_main)


def load_settings() -> Settings:
    return Settings(
        data_dir=Path(os.environ.get("DATA_DIR", REPO_ROOT / "data")),
        kg_dir=Path(os.environ.get("KG_DIR", REPO_ROOT / "kg")),
        fixtures_dir=Path(os.environ.get("FIXTURES_DIR", REPO_ROOT / "fixtures")),
        as_of_date=date.fromisoformat(os.environ.get("AS_OF_DATE", "2026-06-04")),
        # Unset means cognito, so an image run without configuration refuses every request instead
        # of serving mock sign-in. Local runs (compose, make dev, tests) set AUTH_MODE=mock themselves.
        auth_mode=os.environ.get("AUTH_MODE", "cognito"),
        llm_model_fast=os.environ.get("LLM_MODEL_FAST") or None,
        llm_model_main=os.environ.get("LLM_MODEL_MAIN") or None,
    )


# Our own name first; the SDK's usual name is accepted so a reviewer's existing key works locally.
KEY_VARS = ("ANTHROPIC_FUTURE_API_KEY", "ANTHROPIC_API_KEY")


def anthropic_api_key() -> str | None:
    """The key from the environment locally, or from Secrets Manager when deployed.

    The deployed function gets only the secret's id (ANTHROPIC_SECRET_ID); the value never
    appears in IaC, stack outputs or the function's configuration.
    """
    key = next((os.environ[v] for v in KEY_VARS if os.environ.get(v)), None)
    if key:
        return key
    secret_id = os.environ.get("ANTHROPIC_SECRET_ID")
    return _secret_value(secret_id) if secret_id else None


# CloudFront adds this header to every request it sends the API; its value is a generated secret
# (ORIGIN_SECRET_ID names it). Requests without it came straight to the function URL and are refused.
ORIGIN_HEADER = "x-origin-verify"


def origin_secret() -> str | None:
    """The value CloudFront sends, when deployed. Unset locally, so mock and Docker runs need no header."""
    secret_id = os.environ.get("ORIGIN_SECRET_ID")
    return _secret_value(secret_id) if secret_id else None


@lru_cache(maxsize=4)
def _secret_value(secret_id: str) -> str:
    import boto3  # type: ignore[import-not-found]  # provided by the Lambda runtime; not a local dependency

    return clean_secret(boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)["SecretString"])


def clean_secret(raw: str) -> str:
    """The bare key, whether the secret was saved as plain text (maybe with a stray newline or
    quotes) or in the console's key/value form, which stores a one-entry JSON object."""
    value = raw.strip()
    if value.startswith("{"):
        try:
            parsed = json.loads(value)
        except ValueError:
            return value
        if isinstance(parsed, dict) and len(parsed) == 1:
            value = str(next(iter(parsed.values()))).strip()
    return value.strip("\"'")

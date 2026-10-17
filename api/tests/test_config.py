"""Reading the deployed API key from Secrets Manager."""

from __future__ import annotations

import pytest

from coachkg.config import clean_secret


@pytest.mark.parametrize(
    "raw",
    [
        "sk-test-abc",
        "sk-test-abc\n",
        "  sk-test-abc  ",
        '"sk-test-abc"',
        '{"ANTHROPIC_FUTURE_API_KEY": "sk-test-abc"}',
        '{"key": "sk-test-abc\\n"}',
    ],
)
def test_secret_is_read_as_the_bare_key(raw: str) -> None:
    assert clean_secret(raw) == "sk-test-abc"


def test_multi_entry_json_is_left_alone() -> None:
    raw = '{"a": "1", "b": "2"}'
    assert clean_secret(raw) == raw


def test_refusal_fallback_models_are_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    from coachkg.llm import fallback_models

    monkeypatch.delenv("LLM_FALLBACK_MODELS", raising=False)
    monkeypatch.setenv("LLM_MODEL_MAIN", "main-model")
    assert fallback_models() == {"main-model"}
    monkeypatch.setenv("LLM_FALLBACK_MODELS", "a, b")
    assert fallback_models() == {"a", "b"}
    monkeypatch.setenv("LLM_FALLBACK_MODELS", "none")
    assert fallback_models() == frozenset()


def test_key_falls_back_to_the_sdk_name(monkeypatch: pytest.MonkeyPatch) -> None:
    from coachkg.config import anthropic_api_key

    monkeypatch.delenv("ANTHROPIC_SECRET_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_FUTURE_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-sdk")
    assert anthropic_api_key() == "sk-test-sdk"
    monkeypatch.setenv("ANTHROPIC_FUTURE_API_KEY", "sk-test-ours")
    assert anthropic_api_key() == "sk-test-ours"

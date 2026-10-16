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

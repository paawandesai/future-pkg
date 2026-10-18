"""Stored eval results quote no assessment member text (NOTICE: it is not redistributed)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from coachkg.config import REPO_ROOT

RESULTS = REPO_ROOT / "eval" / "results"


def _run_eval() -> Any:
    spec = importlib.util.spec_from_file_location("run_eval", REPO_ROOT / "eval" / "run_eval.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    return []


def test_eval_results_quote_no_member_text(data_dir: Path) -> None:
    ev = _run_eval()
    record = json.loads((data_dir / "member-context.json").read_text())
    sources, ours = ev.member_text(record), ev.our_text()
    assert sources
    leaks = []
    for path in sorted(RESULTS.iterdir()):
        raw = path.read_text()
        text = "\n".join(_strings(json.loads(raw))) if path.suffix == ".json" else raw
        # Lengths and locations only: the test never prints member text.
        leaks += [
            f"{path.name}: source {k} chars {i}-{i + n}" for k, i, n in ev.leaked_spans(text, sources, ours)
        ]
    assert not leaks, leaks


def test_redaction_replaces_quoted_member_text() -> None:
    ev = _run_eval()
    sources = ["Knocked out the whole session today, felt great after it."]
    answer = {"answer": ['She wrote "Knocked out the whole session today" and more.', "short: felt great"]}
    out = ev.redact(answer, sources)
    assert out["answer"][0] == f'She wrote "{ev.PLACEHOLDER}" and more.'
    assert out["answer"][1] == "short: felt great"  # under 24 characters: kept
    assert ev.leaked_spans(json.dumps(out), sources) == []
    # Text we wrote ourselves that happens to match is not member text.
    assert ev.redact("the whole session today, felt", sources, ours="the whole session today, felt") == (
        "the whole session today, felt"
    )


def test_a_negation_only_counts_before_the_claim_in_its_clause() -> None:
    ev = _run_eval()
    pat = "knee is (fully )?healed"
    assert not ev.asserts(pat, "I can't confirm the knee is healed.")
    assert not ev.asserts(pat, "The member says the knee is healed, so check with them.")
    assert not ev.asserts(pat, "If the knee is healed, the coach can lift the restriction.")
    assert ev.asserts(pat, "The knee is healed, so nothing is restricted.")
    assert ev.asserts(pat, "Nothing is restricted because the knee is healed.")
    assert ev.asserts(pat, "There's no restriction, and the knee is fully healed.")

"""Concept resolver (critical path 1): exact, fuzzy, laterality, and no-match behaviour."""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from coachkg.config import REPO_ROOT
from coachkg.kg.graph import NetworkXStore
from coachkg.kg.rules import authored_alt_labels
from coachkg.resolver import ACCEPT, Resolver

CASES = yaml.safe_load((REPO_ROOT / "api" / "tests" / "resolver_cases.yaml").read_text())


@pytest.fixture(scope="module")
def resolver(graph: NetworkXStore) -> Resolver:
    return Resolver(graph, authored_alt_labels(REPO_ROOT / "kg"))


def _outcome(res: Any) -> str:
    out: str = res.concept if res.status == "accepted" else res.status
    return out


@pytest.mark.parametrize("case", CASES["body"], ids=lambda c: c["text"])
def test_body_mentions(resolver: Resolver, case: dict[str, Any]) -> None:
    m = resolver.parse_body_mention(case["text"])
    assert _outcome(m.resolution) == case["expect"], m.resolution.as_trace()
    if "side" in case:
        assert m.side == case["side"]


@pytest.mark.parametrize("case", CASES["other"], ids=lambda c: c["text"])
def test_other_concepts(resolver: Resolver, case: dict[str, Any]) -> None:
    res = resolver.resolve(case["text"], case["kinds"])
    assert _outcome(res) == case["expect"], res.as_trace()


def test_confidence_is_reported(resolver: Resolver) -> None:
    exact = resolver.parse_body_mention("left knee").resolution
    assert exact.method == "exact" and exact.score == 1.0
    fuzzy = resolver.parse_body_mention("sholder").resolution
    assert fuzzy.method == "fuzzy" and ACCEPT <= fuzzy.score < 1.0
    assert fuzzy.as_trace()["score"] == round(fuzzy.score, 2)


def test_find_mentions_in_free_text(resolver: Resolver) -> None:
    found = resolver.find_body_mentions(
        "Upper body today, her left knee is still bothering her. No deadlifts."
    )
    assert [(m.resolution.concept, m.side) for m in found if m.injury] == [("region:knee", "left")]
    # "upper body" is found but not treated as an injury: no pain cue in its clause.
    assert [(m.resolution.concept, m.injury) for m in found if not m.injury] == [("region:upper_limb", False)]


def test_find_mentions_keeps_multiple(resolver: Resolver) -> None:
    found = resolver.find_body_mentions("sore right ankle and some low back pain")
    assert {(m.resolution.concept, m.side) for m in found if m.injury} == {
        ("region:ankle", "right"),
        ("condition:low_back_pain", None),
    }

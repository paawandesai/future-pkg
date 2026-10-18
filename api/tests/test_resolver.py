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


@pytest.mark.parametrize(
    ("text", "injured"),
    [
        # The brief's own example: the knee is the injury, "lower-body" is the focus.
        ("lower-body exercises that avoid aggravating a knee injury", {"region:knee"}),
        ("lower body work and her knee is bothering her", {"region:knee"}),
        ("careful with her knee, lower body", {"region:knee"}),
        ("knee feels great, shoulder is sore", {"region:shoulder"}),
        # Coordinated mentions share the cue.
        ("her right knee and left shoulder hurt", {"region:knee", "region:shoulder"}),
    ],
)
def test_pain_cues_attach_to_the_right_mention(resolver: Resolver, text: str, injured: set[str]) -> None:
    found = resolver.find_body_mentions(text)
    assert {m.resolution.concept for m in found if m.injury} == injured


@pytest.mark.parametrize(
    ("text", "concept", "side"),
    [
        # A phrase that doesn't resolve as a whole falls back to the body name inside it.
        ("knee surgery three weeks ago", "region:knee", None),
        ("post-op knee", "region:knee", None),
        ("tennis elbow on the right", "region:elbow", "right"),
        ("golfer's elbow", "region:elbow", None),
        ("ACL tear", "region:knee", None),
        ("jumper's knee", "region:knee", None),
        ("IT band syndrome", "region:knee", None),
        ("patellar tendinitis", "region:patella", None),
        ("achilles tendinitis", "region:ankle", None),
        ("plantar fasciitis in her left foot", "region:ankle", "left"),
        ("shin splints", "region:ankle", None),
        ("carpal tunnel in her wrist", "region:wrist", None),
        ("wrist is broken", "region:wrist", None),
        ("shoulder impingement", "region:shoulder", None),
        ("herniated disc", "region:lumbar_spine", None),
        ("sciatica", "region:lumbar_spine", None),
        ("neck is stiff", "region:cervical_spine", None),
        ("whiplash from a car accident", "region:cervical_spine", None),
        ("inflamed knee", "region:knee", None),
        ("arthritis in both knees", "region:knee", "both"),
        # Muscles resolve to the muscle; the safety filter restricts the joints it acts on.
        ("pulled hamstring", "muscle:hamstrings", None),
        ("calf strain on the left", "muscle:calves", "left"),
        ("groin pull", "muscle:hip adductors", None),
        ("pec tear", "muscle:chest", None),
        ("hip flexor is tight", "muscle:hip flexors", None),
        # Region names still win over a muscle with the same label.
        ("lower back", "region:lumbar_spine", None),
    ],
)
def test_injury_phrasings_resolve_to_the_body_name_inside(
    resolver: Resolver, text: str, concept: str, side: str | None
) -> None:
    m = resolver.parse_body_mention(text)
    assert (m.resolution.status, m.resolution.concept, m.side) == ("accepted", concept, side)


def test_two_body_names_in_one_mention_are_ambiguous(resolver: Resolver) -> None:
    m = resolver.parse_body_mention("sciatica down the left leg")
    assert m.resolution.status == "ambiguous"
    assert {c.concept for c in m.resolution.candidates} == {"region:lumbar_spine", "region:lower_limb"}


PROBE_INJURIES = [
    ("she tore her ACL last year, go easy", "region:knee"),
    ("she had knee surgery three weeks ago", "region:knee"),
    ("post-op knee, week 4", "region:knee"),
    ("knee replacement in March", "region:knee"),
    ("she pulled her hamstring yesterday", "muscle:hamstrings"),
    ("groin pull", "muscle:hip adductors"),
    ("her achilles is flaring up", "region:ankle"),
    ("shin splints", "region:ankle"),
    ("tennis elbow on the right", "region:elbow"),
    ("carpal tunnel in her wrist", "region:wrist"),
    ("her wrist is broken", "region:wrist"),
    ("stress fracture in her foot", "region:ankle"),
    ("twisted her ankle", "region:ankle"),
    ("shoulder impingement", "region:shoulder"),
    ("her rotator cuff is torn", "muscle:rotator cuff"),
    ("herniated disc", "region:lumbar_spine"),
    ("her SI joint is irritated", "region:lumbar_spine"),
    ("her neck is stiff", "region:cervical_spine"),
    ("her knee feels unstable", "region:knee"),
    ("her knee gave out on the stairs", "region:knee"),
    ("knee swelling after the run", "region:knee"),
    ("swollen and flared up knee", "region:knee"),
    ("her back went out", "region:spine"),
    ("pec tear", "muscle:chest"),
    # Hedged or everyday wording (audit 2026-10-18).
    ("go easy on her knee", "region:knee"),
    ("watch her knee today", "region:knee"),
    ("mind her knee", "region:knee"),
    ("her knee isn't great", "region:knee"),
    ("her knee's been giving her trouble", "region:knee"),
    ("her knee is not 100% yet", "region:knee"),
    ("her left knee is killing her", "region:knee"),
    ("her knee popped yesterday", "region:knee"),
    ("gentle with the shoulder", "region:shoulder"),
]


@pytest.mark.parametrize("text", ["her kneee is sore", "left kne hurts", "her sholder hurts"])
def test_misspelt_body_word_next_to_a_pain_cue_is_a_mention(resolver: Resolver, text: str) -> None:
    """A typo can't slip past the scan: it becomes an injury mention that resolves or blocks."""
    found = [m for m in resolver.find_body_mentions(text) if m.injury]
    assert found and all(m.resolution.status in ("accepted", "ambiguous", "no_match") for m in found)


@pytest.mark.parametrize(("text", "concept"), PROBE_INJURIES)
def test_scan_alone_catches_common_injury_phrasings(resolver: Resolver, text: str, concept: str) -> None:
    """The backstop when the model returns no injury mention at all."""
    found = resolver.find_body_mentions(f"45 minutes, lower body. {text}")
    assert concept in {m.resolution.concept for m in found if m.injury}


@pytest.mark.parametrize(
    "text",
    [
        "lower body today and avoid deadlifts",
        "Lower body, avoid deadlifts",
        "Upper body, avoid shoulder press",
        "stiff leg deadlifts and lower body",
        "glutes and hamstrings today",
        "upper body pull day",
        "her knee is fine now, ignore it",
        "easy upper body day",
        "watch the clock, 30 minutes",
        "mind muscle connection on curls",
        "gentle full body session",
    ],
)
def test_focus_phrases_are_not_injuries(resolver: Resolver, text: str) -> None:
    assert not [m.text for m in resolver.find_body_mentions(text) if m.injury]

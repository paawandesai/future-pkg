"""Concept resolver: free text -> graph concepts, with a confidence that goes into the trace.

Order: exact match on SKOS-style labels (pref + alt), then fuzzy match (rapidfuzz). Thresholds:
exact = 1.0; fuzzy >= 0.90 accepted; 0.75-0.90 ambiguous; below 0.75 no match.
The vector pass from the plan is not implemented (scope cut, see README).

Injury handling is fail-closed and lives in the safety layer; this module only reports what it
found and how sure it is. ``find_body_mentions`` scans text deterministically so a restriction
mentioned in a request is never lost even if the language model misses it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from rapidfuzz import fuzz, process

from coachkg.kg.graph import NetworkXStore

ACCEPT = 0.90
AMBIGUOUS = 0.75

Kind = Literal["region", "condition", "family", "exercise", "equipment", "muscle", "pattern"]
Side = Literal["left", "right", "both"]
Status = Literal["accepted", "ambiguous", "no_match"]

_SIDE_WORDS = {
    "left": "left",
    "lt": "left",
    "l": "left",
    "right": "right",
    "rt": "right",
    "r": "right",
    "both": "both",
    "bilateral": "both",
}
_FILLER = {
    "her",
    "his",
    "my",
    "their",
    "the",
    "a",
    "an",
    "is",
    "its",
    "it's",
    "of",
    "on",
    "side",
    "still",
    "some",
    "bit",
}
# Words that turn a body-part mention into an injury or pain mention.
PAIN_CUES = {
    "pain",
    "painful",
    "hurt",
    "hurts",
    "hurting",
    "sore",
    "soreness",
    "ache",
    "aches",
    "achy",
    "aching",
    "bothering",
    "bugging",
    "injured",
    "injury",
    "tweaked",
    "strained",
    "strain",
    "sprained",
    "sprain",
    "flare",
    "flared",
    "tender",
    "swollen",
    "recovering",
    "rehab",
    "bad",
    "dodgy",
    "tight",
    "niggle",
    "issue",
    "issues",
    "problem",
    "problems",
    "careful",
    "avoid",
    "protect",
    "aggravate",
    "aggravating",
    "aggravated",
    "spare",
}
# Cues that point at what follows them ("avoid aggravating a knee injury", "careful with her knee").
_FORWARD_CUES = {"avoid", "careful", "protect", "aggravate", "aggravating", "spare"}
_COORDINATION = {
    "and",
    "or",
    "&",
    "plus",
    "her",
    "his",
    "their",
    "the",
    "my",
    "both",
    "left",
    "right",
    "l",
    "r",
}


def normalise(text: str) -> str:
    text = text.lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9' -]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _squash(text: str) -> str:
    """'kettle bell' and 'kettlebell' compare equal; also drops a trailing plural s."""
    s = normalise(text).replace(" ", "").replace("-", "").replace("'", "")
    return s[:-1] if s.endswith("s") and len(s) > 4 else s


@dataclass(frozen=True)
class Candidate:
    concept: str
    label: str
    score: float


@dataclass(frozen=True)
class Resolution:
    text: str
    status: Status
    method: Literal["exact", "fuzzy", "none"]
    concept: str | None
    label: str | None
    score: float
    candidates: tuple[Candidate, ...] = field(default_factory=tuple)

    def as_trace(self) -> dict[str, object]:
        return {
            "text": self.text,
            "status": self.status,
            "method": self.method,
            "concept": self.concept,
            "score": round(self.score, 2),
            "candidates": [{"concept": c.concept, "score": round(c.score, 2)} for c in self.candidates],
        }


@dataclass(frozen=True)
class BodyMention:
    text: str
    side: Side | None
    resolution: Resolution
    # True when the mention sits in a clause with a pain/injury cue, or names a condition.
    injury: bool = True


class Resolver:
    def __init__(self, store: NetworkXStore, extra_labels: dict[str, list[str]] | None = None) -> None:
        self._entries: dict[Kind, list[tuple[str, str, str]]] = {}
        for kind in ("region", "condition", "family", "exercise", "equipment", "muscle", "pattern"):
            rows = []
            for node in store.nodes(kind):
                d = store.node(node)
                labels = [d["label"], *d.get("alt_labels", [])]
                if kind == "exercise" and extra_labels:
                    labels += extra_labels.get(d["label"], [])
                for lab in labels:
                    rows.append((node, d["label"], lab))
            self._entries[kind] = rows
        self._exact: dict[Kind, dict[str, set[tuple[str, str]]]] = {}
        for kind, rows in self._entries.items():
            idx: dict[str, set[tuple[str, str]]] = {}
            for node, pref, lab in rows:
                idx.setdefault(_squash(lab), set()).add((node, pref))
            self._exact[kind] = idx

    def resolve(self, text: str, kinds: Iterable[Kind]) -> Resolution:
        kinds = list(kinds)
        key = _squash(text)
        exact = {hit for k in kinds for hit in self._exact[k].get(key, set())}
        if len(exact) == 1:
            node, pref = next(iter(exact))
            return Resolution(text, "accepted", "exact", node, pref, 1.0, (Candidate(node, pref, 1.0),))
        if len(exact) > 1:
            cands = tuple(sorted((Candidate(n, p, 1.0) for n, p in exact), key=lambda c: c.concept))
            return Resolution(text, "ambiguous", "exact", None, None, 1.0, cands)

        choices = [(node, pref, lab) for k in kinds for node, pref, lab in self._entries[k]]
        if not choices or not key:
            return Resolution(text, "no_match", "none", None, None, 0.0)
        # Whole-string similarity only (no partial matching): "kne" must not match "front of the knee".
        scored = process.extract(key, [_squash(c[2]) for c in choices], scorer=fuzz.ratio, limit=8)
        scored += process.extract(
            normalise(text), [normalise(c[2]) for c in choices], scorer=fuzz.token_sort_ratio, limit=8
        )
        best: dict[str, Candidate] = {}
        for _, score, i in scored:
            node, pref, _ = choices[i]
            s = score / 100.0
            if node not in best or best[node].score < s:
                best[node] = Candidate(node, pref, s)
        ranked = sorted(best.values(), key=lambda c: -c.score)
        top = ranked[0]
        close = tuple(c for c in ranked if c.score >= AMBIGUOUS)
        if top.score >= ACCEPT and (len(close) == 1 or close[1].score < top.score - 0.05):
            return Resolution(text, "accepted", "fuzzy", top.concept, top.label, top.score, close or (top,))
        if top.score >= AMBIGUOUS:
            return Resolution(text, "ambiguous", "fuzzy", None, None, top.score, close)
        return Resolution(text, "no_match", "none", None, None, top.score, tuple(ranked[:3]))

    def parse_body_mention(self, text: str) -> BodyMention:
        """'her left knee' -> side=left, region=knee. Side words are removed before resolving."""
        words = normalise(text).split()
        side: Side | None = None
        rest = []
        for w in words:
            if w in _SIDE_WORDS and side is None:
                side = _SIDE_WORDS[w]  # type: ignore[assignment]
            elif w not in _FILLER:
                rest.append(w)
        # A condition name may contain a cue word ("lower back pain", "sprained ankle"): try the
        # phrase as written first, then without cue words ("bad lower back" -> "lower back").
        full = self.resolve(" ".join(rest), ["region", "condition"])
        if full.status == "accepted":
            return BodyMention(text, side, full)
        stripped = " ".join(w for w in rest if w not in PAIN_CUES)
        return BodyMention(text, side, self.resolve(stripped, ["region", "condition"]))

    def find_body_mentions(self, text: str) -> list[BodyMention]:
        """Deterministic scan for region or condition names (n-grams up to 4 words) in text.

        A pain cue ("sore", "bothering", ...) marks the body mention it belongs to as an injury: a
        forward cue ("avoid", "careful with", "protect") marks the next mention after it, any other
        cue marks the nearest one. Mentions joined by "and"/"or" share the mark ("her right knee
        and left shoulder hurt"). A condition name always counts. Other regions are returned with
        injury=False: they are probably a training focus ("lower-body exercises that avoid
        aggravating a knee injury" restricts the knee, not the lower body).
        """
        found: list[BodyMention] = []
        for clause in re.split(r"[.;,!?]|\bbut\b", text.lower()):
            words = normalise(clause).split()
            spans: list[tuple[int, int, str, bool]] = []  # start, end (exclusive), phrase, condition
            taken: set[int] = set()
            for n in (4, 3, 2, 1):
                for i in range(len(words) - n + 1):
                    span = set(range(i, i + n))
                    if span & taken:
                        continue
                    phrase = " ".join(words[i : i + n])
                    regions = self._exact["region"].get(_squash(phrase), set())
                    conditions = self._exact["condition"].get(_squash(phrase), set())
                    if not regions and not conditions:
                        continue
                    taken |= span
                    spans.append((i, i + n, phrase, bool(conditions)))
            spans.sort()
            marked = {k for k, sp in enumerate(spans) if sp[3]}
            for p, w in enumerate(words):
                if w not in PAIN_CUES or p in taken or not spans:
                    continue
                after = [k for k, sp in enumerate(spans) if sp[0] > p]
                if w in _FORWARD_CUES and after:
                    marked.add(after[0])
                    continue
                dist = [max(sp[0] - p, p - sp[1] + 1) for sp in spans]
                marked.add(min(range(len(spans)), key=lambda k: (dist[k], spans[k][0])))
            for k in range(len(spans) - 1):  # coordination: "knee and shoulder", "hip or back"
                between = set(words[spans[k][1] : spans[k + 1][0]])
                if between and between <= _COORDINATION and ({k, k + 1} & marked):
                    marked |= {k, k + 1}
            for k, (i, _end, phrase, _cond) in enumerate(spans):
                side: Side | None = None
                for j in range(max(0, i - 2), i):
                    if words[j] in _SIDE_WORDS:
                        side = _SIDE_WORDS[words[j]]  # type: ignore[assignment]
                res = self.resolve(phrase, ["region", "condition"])
                found.append(BodyMention(phrase, side, res, injury=k in marked))
        return found

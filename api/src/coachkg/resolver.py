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
from dataclasses import dataclass, field, replace
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
    "pains",
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
    "acting",
    "injured",
    "injury",
    "injuries",
    "tweaked",
    "strained",
    "strain",
    "strains",
    "sprained",
    "sprain",
    "sprains",
    "pulled",
    "twisted",
    "rolled",
    "tear",
    "torn",
    "tore",
    "ruptured",
    "rupture",
    "broken",
    "broke",
    "fracture",
    "fractured",
    "dislocated",
    "dislocation",
    "surgery",
    "surgeries",
    "operation",
    "operated",
    "op",
    "post-op",
    "postop",
    "replacement",
    "replaced",
    "reconstruction",
    "repair",
    "repaired",
    "flare",
    "flared",
    "flaring",
    "flare-up",
    "tender",
    "swollen",
    "swelling",
    "inflamed",
    "inflammation",
    "unstable",
    "instability",
    "stiff",
    "stiffness",
    "irritated",
    "cranky",
    "tendinitis",
    "tendonitis",
    "tendinopathy",
    "bursitis",
    "arthritis",
    "osteoarthritis",
    "arthritic",
    "impingement",
    "impinged",
    "clicks",
    "clicking",
    "recovering",
    "rehab",
    "rehabbing",
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
    # Injury names whose other words are body words ("sciatica", "herniated disc", "shin splints").
    "sciatica",
    "whiplash",
    "fasciitis",
    "splints",
    "herniated",
    "bulging",
    "slipped",
    "carpal",
    "syndrome",
    "frozen",
}
# Cue words that name an exercise when followed by these words ("stiff leg deadlift").
_NOT_CUES = {("stiff", "leg"), ("stiff", "legged"), ("rolled", "up")}
# Two-word cues that are only cues together ("tennis elbow", "her back went out").
_CUE_PHRASES = {
    ("tennis", "elbow"),
    ("golfer's", "elbow"),
    ("golfers", "elbow"),
    ("jumper's", "knee"),
    ("jumpers", "knee"),
    ("groin", "pull"),
    ("hamstring", "pull"),
    ("calf", "pull"),
    ("muscle", "pull"),
    ("gave", "out"),
    ("gave", "way"),
    ("gives", "way"),
    ("giving", "way"),
    ("went", "out"),
}
# Cues that point at what follows them ("avoid aggravating a knee injury", "careful with her knee").
_FORWARD_CUES = {"avoid", "careful", "protect", "aggravate", "aggravating", "spare"}
# Words that may follow a forward cue without naming what it points at ("knee, be careful with it").
_CUE_TAIL = {"with", "it", "them", "that", "this", "there", "please", "today", "on", "of", "and", "be"}
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
    method: Literal["exact", "fuzzy", "contained", "none"]
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

    def _exact_body(self, phrase: str) -> Resolution | None:
        """An exact region or condition name; failing that, an exact muscle name ("hamstring")."""
        body: list[list[Kind]] = [["region", "condition"], ["muscle"]]
        for kinds in body:
            r = self.resolve(phrase, kinds)
            if r.method == "exact":
                return r
        return None

    def _contained(self, text: str, words: list[str]) -> Resolution | None:
        """Body names inside a phrase that doesn't resolve as a whole: "knee surgery three weeks
        ago" -> knee, "tennis elbow" -> elbow. Longest names first; one name -> accepted, several
        -> ambiguous (the safety filter then restricts all of them)."""
        found: dict[str, Candidate] = {}
        taken: set[int] = set()
        for n in (4, 3, 2, 1):
            for i in range(len(words) - n + 1):
                span = set(range(i, i + n))
                if span & taken:
                    continue
                r = self._exact_body(" ".join(words[i : i + n]))
                if r is None:
                    continue
                taken |= span
                for c in r.candidates:
                    found.setdefault(c.concept, c)
        if not found:
            return None
        cands = tuple(sorted(found.values(), key=lambda c: c.concept))
        if len(cands) == 1:
            c = cands[0]
            return Resolution(text, "accepted", "contained", c.concept, c.label, 1.0, cands)
        return Resolution(text, "ambiguous", "contained", None, None, 1.0, cands)

    def parse_body_mention(self, text: str) -> BodyMention:
        """'her left knee' -> side=left, region=knee. Side words are removed before resolving.

        Order: the phrase as written, then without cue words ("bad lower back" -> "lower back"),
        exact names first; then a body name inside the phrase ("ACL tear" -> knee, "pulled
        hamstring" -> the hamstrings muscle); then fuzzy matching of the whole phrase."""
        words = normalise(text).split()
        side: Side | None = None
        rest = []
        for w in words:
            if w in _SIDE_WORDS and side is None:
                side = _SIDE_WORDS[w]  # type: ignore[assignment]
            elif w not in _FILLER:
                rest.append(w)
        stripped_words = [w for w in rest if w not in PAIN_CUES]
        stripped = " ".join(stripped_words)
        for phrase in (" ".join(rest), stripped):
            exact = self._exact_body(phrase)
            if exact is not None:
                return BodyMention(text, side, replace(exact, text=phrase))
        inside = self._contained(text, rest)
        if inside is not None:
            return BodyMention(text, side, inside)
        full = self.resolve(" ".join(rest), ["region", "condition"])
        if full.status == "accepted":
            return BodyMention(text, side, full)
        return BodyMention(text, side, self.resolve(stripped, ["region", "condition"]))

    def _name_spans(self, words: list[str]) -> set[int]:
        """Word positions inside an exercise or family name ("shoulder press", "single leg
        deadlift"): a body word there names the exercise, not a body part."""
        out: set[int] = set()
        for n in (4, 3, 2):
            for i in range(len(words) - n + 1):
                key = _squash(" ".join(words[i : i + n]))
                if self._exact["exercise"].get(key) or self._exact["family"].get(key):
                    out |= set(range(i, i + n))
        return out

    def find_body_mentions(self, text: str) -> list[BodyMention]:
        """Deterministic scan for region, condition or muscle names (n-grams up to 4 words) in text.

        A pain cue ("sore", "surgery", "torn", "swollen", ...) marks the body mention it belongs
        to as an injury: a forward cue ("avoid", "careful with", "protect") marks the next mention
        after it, any other cue marks the nearest one. A forward cue followed by something that
        isn't a body word ("avoid deadlifts") marks nothing. Mentions joined by "and"/"or" share the
        mark ("her right knee and left shoulder hurt"). A condition name always counts. Other
        regions are returned with injury=False: they are probably a training focus ("lower-body
        exercises that avoid aggravating a knee injury" restricts the knee, not the lower body).
        Muscle names count only with a cue ("pulled her hamstring"); without one they are focus
        words and are left to the focus reader. Body words inside an exercise name are skipped.
        """
        found: list[BodyMention] = []
        for clause in re.split(r"[.;,!?]|\bbut\b", text.lower()):
            words = normalise(clause).split()
            names = self._name_spans(words)
            # start, end (exclusive), phrase, condition, muscle
            spans: list[tuple[int, int, str, bool, bool]] = []
            taken: set[int] = set(names)
            for n in (4, 3, 2, 1):
                for i in range(len(words) - n + 1):
                    span = set(range(i, i + n))
                    if span & taken:
                        continue
                    phrase = " ".join(words[i : i + n])
                    key = _squash(phrase)
                    regions = self._exact["region"].get(key, set())
                    conditions = self._exact["condition"].get(key, set())
                    muscles = set() if regions or conditions else self._exact["muscle"].get(key, set())
                    if not regions and not conditions and not muscles:
                        continue
                    taken |= span
                    spans.append((i, i + n, phrase, bool(conditions), bool(muscles)))
            spans.sort()
            marked = {k for k, sp in enumerate(spans) if sp[3]}
            cues = [
                p
                for p, w in enumerate(words)
                if w in PAIN_CUES
                and p not in names
                and (w, words[p + 1] if p + 1 < len(words) else "") not in _NOT_CUES
            ]
            cues += [p for p in range(len(words) - 1) if (words[p], words[p + 1]) in _CUE_PHRASES]
            for p in sorted(set(cues)):
                w = words[p]
                if not spans:
                    break
                inside = [k for k, sp in enumerate(spans) if sp[0] <= p < sp[1]]
                if inside:  # the cue is part of the name ("sciatica", "shin splints")
                    marked.add(inside[0])
                    continue
                after = [k for k, sp in enumerate(spans) if sp[0] > p]
                if w in _FORWARD_CUES:
                    if after:
                        marked.add(after[0])
                        continue
                    if set(words[p + 1 :]) - _CUE_TAIL - _FILLER:
                        continue  # "avoid deadlifts": the cue points at something else
                dist = [max(sp[0] - p, p - sp[1] + 1) for sp in spans]
                marked.add(min(range(len(spans)), key=lambda k: (dist[k], spans[k][0])))
            for k in range(len(spans) - 1):  # coordination: "knee and shoulder", "hip or back"
                between = set(words[spans[k][1] : spans[k + 1][0]])
                if between and between <= _COORDINATION and ({k, k + 1} & marked):
                    marked |= {k, k + 1}
            for k, (i, _end, phrase, _cond, muscle) in enumerate(spans):
                if muscle and k not in marked:
                    continue
                side: Side | None = None
                for j in range(max(0, i - 2), i):
                    if words[j] in _SIDE_WORDS:
                        side = _SIDE_WORDS[words[j]]  # type: ignore[assignment]
                res = self.resolve(phrase, ["muscle"] if muscle else ["region", "condition"])
                found.append(BodyMention(phrase, side, res, injury=k in marked))
        return found

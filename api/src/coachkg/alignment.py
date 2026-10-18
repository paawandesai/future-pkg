"""External ontology alignments (SNOMED CT via NCI EVS, Uberon via EBI OLS).

SNOMED is reference-only: we store codes and our own labels. Live responses go to a gitignored
cache as provenance evidence (prov:wasDerivedFrom); nothing from them is committed.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, datetime
from typing import Any

import httpx
import yaml

from coachkg.config import REPO_ROOT

EVS_BASE = "https://api-evsrest.nci.nih.gov/api/v1/concept/snomedct_us"
OLS_BASE = "https://www.ebi.ac.uk/ols4/api/ontologies/uberon/terms"
ALIGN_DIR = REPO_ROOT / "kg" / "alignment"
EVIDENCE_DIR = REPO_ROOT / ".cache" / "evs"


def normalise(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


SIDES = ("left", "right")


def label_matches(our_label: str, live_name: str) -> bool:
    """Our label shares a meaningful word (or its first six letters) with the live name, and both
    name the same side or neither does. Catches a mis-pinned or reused code."""
    ours = set(normalise(our_label).replace(",", " ").split())
    theirs = set(normalise(live_name).replace(",", " ").replace("(", " ").replace(")", " ").split())
    if {s for s in SIDES if s in ours} != {s for s in SIDES if s in theirs}:
        return False
    long_ours = {w for w in ours if len(w) > 3}
    return bool(long_ours & theirs or {w[:6] for w in long_ours} & {w[:6] for w in theirs})


def load_snomed() -> list[dict[str, Any]]:
    data = yaml.safe_load((ALIGN_DIR / "snomed.yaml").read_text())
    return list(data["alignments"])


def load_uberon() -> list[dict[str, Any]]:
    data = yaml.safe_load((ALIGN_DIR / "uberon.yaml").read_text())
    return list(data["alignments"])


def fetch_evs(client: httpx.Client, sctid: str, attempts: int = 4) -> httpx.Response:
    """EVS rate-limits bursts with empty bodies; retry with backoff."""
    resp = client.get(f"{EVS_BASE}/{sctid}", params={"include": "minimal"})
    for i in range(attempts):
        if resp.status_code == 404:
            return resp
        if resp.status_code == 200 and resp.json().get("code") == sctid:
            return resp
        time.sleep(1.5 * (i + 1))
        resp = client.get(f"{EVS_BASE}/{sctid}", params={"include": "minimal"})
    return resp


def record_evidence(sctid: str, resp: httpx.Response) -> dict[str, str]:
    """Write prov:wasDerivedFrom evidence for one lookup to the gitignored cache."""
    body = resp.content
    evidence = {
        "@type": "prov:Entity",
        "prov:wasDerivedFrom": f"{EVS_BASE}/{sctid}",
        "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "response_sha256": hashlib.sha256(body).hexdigest(),
        "terminology_version": str(resp.json().get("version", "")) if resp.status_code == 200 else "",
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / f"{sctid}.json").write_text(json.dumps(evidence, indent=2))
    return evidence

"""External ontology alignments (SNOMED CT via NCI EVS, Uberon via EBI OLS).

SNOMED is reference-only: we store codes and our own labels, plus a hash of the name EVS
returned when the code was pinned. Live responses go to a gitignored cache as provenance
evidence (prov:wasDerivedFrom); nothing from them is committed.

    uv run python -m coachkg.alignment pin     # fill evs_name_sha256 for new entries
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
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


def name_hash(name: str) -> str:
    return hashlib.sha256(normalise(name).encode()).hexdigest()


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


def pin() -> int:
    """Fill evs_name_sha256 on entries that lack it. Prints codes only, never names."""
    path = ALIGN_DIR / "snomed.yaml"
    text = path.read_text()
    with httpx.Client(timeout=20) as client:
        for entry in load_snomed():
            if entry.get("evs_name_sha256"):
                continue
            resp = fetch_evs(client, entry["sctid"])
            if resp.status_code != 200:
                print(f"{entry['sctid']}: HTTP {resp.status_code}", file=sys.stderr)
                return 1
            digest = name_hash(resp.json()["name"])
            needle = f'sctid: "{entry["sctid"]}",'
            text = text.replace(needle, f'{needle} evs_name_sha256: "{digest}",', 1)
            print(f"pinned {entry['sctid']}")
            time.sleep(1.0)
    path.write_text(text)
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["pin"]:
        sys.exit(pin())
    print(__doc__)

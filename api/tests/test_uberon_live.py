"""Every Uberon IRI in kg/alignment/uberon.yaml resolves at EBI OLS with the recorded label."""

from __future__ import annotations

import httpx
import pytest

from coachkg.alignment import OLS_BASE, load_uberon

pytestmark = pytest.mark.live


@pytest.mark.parametrize("entry", load_uberon(), ids=lambda e: e["uberon"])
def test_uberon_label(entry: dict[str, str]) -> None:
    resp = httpx.get(OLS_BASE, params={"obo_id": entry["uberon"]}, timeout=20)
    assert resp.status_code == 200
    terms = resp.json().get("_embedded", {}).get("terms", [])
    assert terms, f"{entry['uberon']} not found"
    assert terms[0]["label"] == entry["uberon_label"]

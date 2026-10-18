"""Build-time check: every SCTID in kg/alignment/snomed.yaml resolves live at NCI EVS, is active,
and its live name still matches our label (a shared word, the same side). A 404, an inactive
concept or a name that no longer matches fails.
Evidence for each lookup is written to .cache/evs/ (gitignored) as prov:wasDerivedFrom."""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest

from coachkg.alignment import fetch_evs, label_matches, load_snomed, record_evidence

pytestmark = pytest.mark.live


@pytest.fixture(scope="module")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(timeout=20) as c:
        yield c


@pytest.mark.parametrize("entry", load_snomed(), ids=lambda e: f"{e['concept']}:{e['side']}:{e['sctid']}")
def test_sctid_resolves_with_expected_name(client: httpx.Client, entry: dict[str, str]) -> None:
    resp = fetch_evs(client, entry["sctid"])
    assert resp.status_code == 200, f"EVS returned {resp.status_code} for {entry['sctid']}"
    record_evidence(entry["sctid"], resp)
    body = resp.json()
    assert body.get("active") is True
    # Printed on failure: the code and our label only, never the SNOMED name.
    assert label_matches(entry["our_label"], body["name"]), (
        f"{entry['sctid']} no longer matches {entry['our_label']}"
    )

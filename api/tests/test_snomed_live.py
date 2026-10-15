"""Build-time check: every SCTID in kg/alignment/snomed.yaml resolves live at NCI EVS, is active,
and still has the name it had when pinned. A 404, an inactive concept or a changed name fails.
Evidence for each lookup is written to .cache/evs/ (gitignored) as prov:wasDerivedFrom."""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest

from coachkg.alignment import fetch_evs, load_snomed, name_hash, normalise, record_evidence

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
    assert name_hash(body["name"]) == entry["evs_name_sha256"], "EVS name changed since pinning"
    # Our label must share a meaningful word with the live name (catches a mis-pinned code).
    ours = {w for w in normalise(entry["our_label"]).split() if len(w) > 3}
    theirs = set(normalise(body["name"]).replace(",", " ").split())
    assert ours & theirs or {w[:6] for w in ours} & {w[:6] for w in theirs}

"""Every Wikidata item in kg/alignment/wikidata.yaml exists with the recorded English label."""

from __future__ import annotations

import time

import httpx
import pytest

from coachkg.skos import load_wikidata

pytestmark = pytest.mark.live


def test_wikidata_labels() -> None:
    entries = load_wikidata()
    ids = sorted({e["wikidata"] for e in entries})
    params = {
        "action": "wbgetentities",
        "ids": "|".join(ids),
        "props": "labels",
        "languages": "en",
        "format": "json",
    }
    headers = {"User-Agent": "future-pkg-alignment-check/0.1 (demo project)"}
    for attempt in range(5):  # Wikidata rate-limits bursts with 429
        resp = httpx.get("https://www.wikidata.org/w/api.php", params=params, headers=headers, timeout=30)
        if resp.status_code != 429:
            break
        time.sleep(int(resp.headers.get("retry-after", "0") or 0) or 5 * (attempt + 1))
    assert resp.status_code == 200
    found = resp.json()["entities"]
    for e in entries:
        item = found.get(e["wikidata"], {})
        assert "missing" not in item, e["wikidata"]
        assert item["labels"]["en"]["value"] == e["wikidata_label"], e["wikidata"]

"""Offline checks on the alignment files: they point at real concepts and carry no SNOMED text."""

from __future__ import annotations

from coachkg.alignment import load_snomed, load_uberon
from coachkg.kg.graph import NetworkXStore

ALLOWED_SNOMED_KEYS = {"concept", "side", "sctid", "match", "our_label", "evs_name_sha256"}


def test_alignments_reference_graph_concepts(graph: NetworkXStore) -> None:
    nodes = set(graph.nodes("region")) | set(graph.nodes("condition"))
    for entry in load_snomed() + load_uberon():
        assert entry["concept"] in nodes, entry["concept"]


def test_snomed_entries_store_codes_and_our_labels_only() -> None:
    seen = set()
    for entry in load_snomed():
        assert set(entry) <= ALLOWED_SNOMED_KEYS, set(entry) - ALLOWED_SNOMED_KEYS
        assert entry["sctid"].isdigit()
        assert len(entry.get("evs_name_sha256", "")) == 64, f"{entry['sctid']} not pinned"
        key = (entry["concept"], entry["side"])
        assert key not in seen
        seen.add(key)


def test_every_dataset_joint_region_is_aligned(graph: NetworkXStore) -> None:
    aligned = {e["concept"] for e in load_snomed()}
    for region in graph.nodes("region"):
        if graph.in_edges(region, "stresses", trusted_only=True):
            assert region in aligned, f"{region} is loaded by dataset exercises but has no SNOMED alignment"

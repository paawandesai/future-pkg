"""Offline checks on the alignment files: they point at real concepts and carry no SNOMED text."""

from __future__ import annotations

from rdflib import Graph
from rdflib.namespace import SKOS

from coachkg.alignment import label_matches, load_snomed, load_uberon
from coachkg.config import REPO_ROOT
from coachkg.kg.graph import NetworkXStore
from coachkg.skos import build, load_wikidata

ALLOWED_SNOMED_KEYS = {"concept", "side", "sctid", "match", "our_label"}


def test_alignments_reference_graph_concepts(graph: NetworkXStore) -> None:
    nodes = {n for k in ("region", "condition", "muscle", "equipment") for n in graph.nodes(k)}
    for entry in load_snomed() + load_uberon() + load_wikidata():
        assert entry["concept"] in nodes, entry["concept"]


def test_snomed_entries_store_codes_and_our_labels_only() -> None:
    seen = set()
    for entry in load_snomed():
        assert set(entry) <= ALLOWED_SNOMED_KEYS, set(entry) - ALLOWED_SNOMED_KEYS
        assert entry["sctid"].isdigit()
        key = (entry["concept"], entry["side"])
        assert key not in seen
        seen.add(key)


def test_the_label_check_needs_a_shared_word_and_the_same_side() -> None:
    assert label_matches("Left knee joint", "Structure of left knee joint")
    assert not label_matches("Left knee joint", "Structure of right knee joint")
    assert not label_matches("Knee joint", "Structure of left knee joint")
    assert not label_matches("Ankle sprain", "Fracture of wrist")


def test_every_dataset_joint_region_is_aligned(graph: NetworkXStore) -> None:
    aligned = {e["concept"] for e in load_snomed()}
    for region in graph.nodes("region"):
        if graph.in_edges(region, "stresses", trusted_only=True):
            assert region in aligned, f"{region} is loaded by dataset exercises but has no SNOMED alignment"


def test_every_muscle_group_has_an_uberon_match(graph: NetworkXStore) -> None:
    aligned = {e["concept"] for e in load_uberon()}
    assert set(graph.nodes("muscle")) <= aligned


def test_skos_export_is_current_and_carries_every_match(graph: NetworkXStore) -> None:
    built = build(graph)
    on_disk = Graph().parse(REPO_ROOT / "kg" / "export" / "coachkg-skos.ttl")
    assert set(built) == set(on_disk), (
        "regenerate: uv run python -m coachkg.skos > ../kg/export/coachkg-skos.ttl"
    )
    matches = [
        t
        for t in built
        if t[1] in (SKOS.exactMatch, SKOS.closeMatch, SKOS.broadMatch, SKOS.narrowMatch, SKOS.relatedMatch)
    ]
    assert len(matches) == len(load_snomed()) + len(load_uberon()) + len(load_wikidata())

"""Ingest: taxonomy counts are derived from the file, and every edge carries provenance."""

from __future__ import annotations

import json
from pathlib import Path

from coachkg.data import Exercise
from coachkg.kg.graph import NetworkXStore, ex_node, is_trusted


def test_counts_derived_from_file(data_dir: Path, graph: NetworkXStore) -> None:
    raw = json.loads((data_dir / "exercises.json").read_text())
    dataset_ex = [n for n in graph.nodes("exercise") if graph.node(n)["origin"] == "dataset"]
    assert len(dataset_ex) == len(raw)

    def distinct(field: str) -> int:
        return len({v for row in raw for v in row[field]})

    # Counts come from the file itself; the graph must agree with them, whatever they are.
    muscles = {e.dst for n in dataset_ex for e in graph.out_edges(n, "targets")}
    patterns = {e.dst for n in dataset_ex for e in graph.out_edges(n, "has-pattern")}
    equipment = {e.dst for n in dataset_ex for e in graph.out_edges(n, "requires")}
    joints = {e.dst for n in dataset_ex for e in graph.out_edges(n, "stresses") if e.prov == "dataset"}
    assert len(muscles) == distinct("muscle_groups")
    assert len(patterns) == distinct("movement_patterns")
    assert len(equipment) == distinct("equipment_required")
    assert len(joints) == distinct("joints_loaded")


def test_every_edge_has_provenance(graph: NetworkXStore) -> None:
    for e in graph.all_edges():
        assert e.prov == "dataset" or e.prov == "model" or e.prov.startswith("human:")
        assert e.source


def test_unsigned_rules_are_model_attributed(graph: NetworkXStore) -> None:
    part_of = [e for e in graph.all_edges() if e.kind == "part-of"]
    assert part_of
    # Drafts stay model-attributed until a reviewer signs the file.
    assert all(e.prov == "model" or e.prov.startswith("human:") for e in part_of)


def test_left_side_rows_stress_left_only(catalog: list[Exercise], graph: NetworkXStore) -> None:
    left = next(e for e in catalog if e.side == "left_leg" and "knee" in e.joints_loaded)
    edges = graph.out_edges(ex_node(left.id), "stresses", trusted_only=True)
    assert {e.attrs["laterality"] for e in edges} == {"left"}


def test_unpaired_bilateral_ids_are_not_invented(catalog: list[Exercise]) -> None:
    ids = {e.id for e in catalog}
    dangling = [e for e in catalog if e.bilateral_pair_id and e.bilateral_pair_id not in ids]
    # The file references right-side rows it does not contain; we keep them as unresolved ids.
    assert dangling
    assert not any(e.side and e.side.startswith("right") for e in catalog)


def test_trusted_filter_hides_model_edges(graph: NetworkXStore) -> None:
    for n in graph.nodes("exercise"):
        for e in graph.out_edges(n, "stresses", trusted_only=True):
            assert is_trusted(e.prov)

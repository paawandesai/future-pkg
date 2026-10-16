"""Movement / clinical graph (KG 1) behind a small store interface.

Every edge carries ``prov`` (``dataset``, ``human:<initials>`` or ``model``) and ``source`` (where it
came from). Readers that make safety decisions pass ``trusted_only=True`` and never see model edges.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any, Protocol

import networkx as nx

from coachkg.data import Exercise
from coachkg.kg.rules import RuleSet

DATASET_SOURCE = "exercises.json@4b8c672"


def is_trusted(prov: str) -> bool:
    return prov == "dataset" or prov.startswith("human:")


def ex_node(exercise_id: str) -> str:
    return f"ex:{exercise_id}"


def region_node(region_id: str) -> str:
    return f"region:{region_id}"


@dataclass(frozen=True)
class Edge:
    src: str
    dst: str
    kind: str
    prov: str
    source: str
    attrs: dict[str, Any] = field(default_factory=dict)


class GraphStore(Protocol):
    def add_node(self, node: str, **attrs: Any) -> None: ...
    def add_edge(self, edge: Edge) -> None: ...
    def node(self, node: str) -> dict[str, Any]: ...
    def nodes(self, kind: str) -> list[str]: ...
    def out_edges(self, node: str, kind: str, trusted_only: bool = False) -> list[Edge]: ...
    def in_edges(self, node: str, kind: str, trusted_only: bool = False) -> list[Edge]: ...


class NetworkXStore:
    """In-process store. ~60 exercises and ~150 concepts fit in memory; traversal is microseconds."""

    def __init__(self) -> None:
        self.g: nx.MultiDiGraph[str] = nx.MultiDiGraph()

    def add_node(self, node: str, **attrs: Any) -> None:
        if node in self.g:
            self.g.nodes[node].update(attrs)
        else:
            self.g.add_node(node, **attrs)

    def add_edge(self, edge: Edge) -> None:
        for n in (edge.src, edge.dst):
            if n not in self.g:
                raise KeyError(f"edge {edge.kind} references unknown node {n}")
        self.g.add_edge(edge.src, edge.dst, key=f"{edge.kind}|{edge.prov}", edge=edge)

    def node(self, node: str) -> dict[str, Any]:
        return dict(self.g.nodes[node])

    def nodes(self, kind: str) -> list[str]:
        return [n for n, d in self.g.nodes(data=True) if d.get("kind") == kind]

    def _edges(
        self, it: Iterable[tuple[str, str, dict[str, Any]]], kind: str, trusted_only: bool
    ) -> list[Edge]:
        out = []
        for _, _, d in it:
            e: Edge = d["edge"]
            if e.kind == kind and (not trusted_only or is_trusted(e.prov)):
                out.append(e)
        return out

    def out_edges(self, node: str, kind: str, trusted_only: bool = False) -> list[Edge]:
        return self._edges(self.g.out_edges(node, data=True), kind, trusted_only)

    def in_edges(self, node: str, kind: str, trusted_only: bool = False) -> list[Edge]:
        return self._edges(self.g.in_edges(node, data=True), kind, trusted_only)

    def all_edges(self) -> Iterator[Edge]:
        for _, _, d in self.g.edges(data=True):
            yield d["edge"]


def _slug(text: str) -> str:
    return text.strip().lower()


def build_movement_graph(catalog: list[Exercise], rules: RuleSet) -> NetworkXStore:
    store = NetworkXStore()

    # Anatomy: regions and part-of (authored, attributed per the file's review).
    anat_prov = rules.anatomy_review.attributed_to
    joint_to_region = {}
    for r in rules.regions:
        store.add_node(
            region_node(r.id), kind="region", label=r.label, alt_labels=r.alt_labels, sided=r.sided
        )
        if r.dataset_joint:
            joint_to_region[r.dataset_joint] = r.id
    for r in rules.regions:
        if r.part_of:
            store.add_edge(
                Edge(region_node(r.id), region_node(r.part_of), "part-of", anat_prov, "kg/rules/anatomy.yaml")
            )

    def add_exercise(e: Exercise, prov: str, source: str) -> None:
        n = ex_node(e.id)
        store.add_node(n, kind="exercise", label=e.name, exercise=e, origin=e.origin, prov=prov)
        for m in e.muscle_groups:
            store.add_node(f"muscle:{_slug(m)}", kind="muscle", label=m)
            store.add_edge(Edge(n, f"muscle:{_slug(m)}", "targets", prov, f"{source} muscle_groups"))
        for p in e.movement_patterns:
            store.add_node(f"pattern:{_slug(p)}", kind="pattern", label=p)
            store.add_edge(Edge(n, f"pattern:{_slug(p)}", "has-pattern", prov, f"{source} movement_patterns"))
        for q in e.equipment_required:
            store.add_node(f"equipment:{_slug(q)}", kind="equipment", label=q)
            store.add_edge(Edge(n, f"equipment:{_slug(q)}", "requires", prov, f"{source} equipment_required"))
        for j in e.joints_loaded:
            store.add_edge(
                Edge(
                    n,
                    region_node(joint_to_region[j]),
                    "stresses",
                    prov,
                    f"{source} joints_loaded",
                    {"laterality": e.laterality},
                )
            )

    for e in catalog:
        add_exercise(e, "dataset", DATASET_SOURCE)
    authored_prov = rules.authored_review.attributed_to
    for e in rules.authored:
        add_exercise(e, authored_prov, "kg/authored/exercises.yaml")

    # Attribute-derived stresses the dataset omits (e.g. Jumping Jack -> knee).
    attr_prov = rules.attributes_review.attributed_to
    by_name = {store.node(n)["label"]: n for n in store.nodes("exercise")}
    for name, a in rules.attributes.items():
        n = by_name[name]
        store.add_node(n, attributes=a, attributes_prov=attr_prov)
        lat = store.node(n)["exercise"].laterality
        for reg in a.extra_stresses:
            store.add_edge(
                Edge(
                    n,
                    region_node(reg),
                    "stresses",
                    attr_prov,
                    "kg/rules/exercise_attributes.yaml",
                    {"laterality": lat},
                )
            )

    # Families: variant-of (exercise -> family) and is-a (family -> family).
    fam_prov = rules.families_review.attributed_to
    for f in rules.families:
        store.add_node(f"family:{f.id}", kind="family", label=f.label, alt_labels=f.alt_labels)
    for f in rules.families:
        if f.is_a:
            store.add_edge(
                Edge(f"family:{f.id}", f"family:{f.is_a}", "is-a", fam_prov, "kg/rules/families.yaml")
            )
        for m in f.members:
            store.add_edge(
                Edge(by_name[m], f"family:{f.id}", "variant-of", fam_prov, "kg/rules/families.yaml")
            )

    # Conditions: affects (condition -> region).
    contra_prov = rules.contra_review.attributed_to
    for c in rules.conditions:
        store.add_node(f"condition:{c.id}", kind="condition", label=c.label, alt_labels=c.alt_labels)
        for reg in c.regions:
            store.add_edge(
                Edge(
                    f"condition:{c.id}",
                    region_node(reg),
                    "affects",
                    contra_prov,
                    "kg/rules/contraindications.yaml",
                )
            )

    # Contraindications: contraindicated-for (exercise -> condition), materialised from the rules
    # so the graph can answer "what is off-limits with this condition?" and the safety filter can
    # cite the edge. Attribute-based hits carry the attributes' provenance too.
    for n in store.nodes("exercise"):
        d = store.node(n)
        ex = d["exercise"]
        for rule in rules.rules:
            if not rule.hits(ex.movement_patterns, d.get("attributes")):
                continue
            by_pattern = bool(set(rule.when.patterns_any or []) & set(ex.movement_patterns))
            store.add_edge(
                Edge(
                    n,
                    f"condition:{rule.condition}",
                    "contraindicated-for",
                    contra_prov,
                    "kg/rules/contraindications.yaml",
                    {
                        "rule": rule.id,
                        "effect": rule.effect,
                        "via": "movement pattern" if by_pattern else "exercise attributes",
                    },
                )
            )

    # Equipment substitutes (ranking only).
    eq_prov = rules.equipment_review.attributed_to
    for s in rules.substitutes:
        missing, use = f"equipment:{_slug(s.missing)}", f"equipment:{_slug(s.use)}"
        store.add_node(missing, kind="equipment", label=s.missing)
        store.add_node(use, kind="equipment", label=s.use)
        store.add_edge(
            Edge(
                use, missing, "substitutes-for", eq_prov, "kg/rules/equipment.yaml", {"patterns": s.patterns}
            )
        )
    _add_labels(store, rules.labels)
    return store


def _add_labels(store: NetworkXStore, labels: dict[str, dict[str, list[str]]]) -> None:
    """Attach kg/vocab/labels.yaml as alt labels. Fails on an unknown concept or a label that
    would point at two concepts of the same kind."""
    for kind, by_pref in labels.items():
        nodes = {store.node(n)["label"]: n for n in store.nodes(kind)}
        taken = {
            _slug(lab): n
            for n in nodes.values()
            for lab in [store.node(n)["label"], *store.node(n).get("alt_labels", [])]
        }
        for pref, extra in by_pref.items():
            if pref not in nodes:
                raise ValueError(f"kg/vocab/labels.yaml: no {kind} called {pref!r}")
            node = nodes[pref]
            for lab in extra:
                other = taken.setdefault(_slug(lab), node)
                if other != node:
                    raise ValueError(f"kg/vocab/labels.yaml: {lab!r} already names {other}")
            store.g.nodes[node]["alt_labels"] = [*store.node(node).get("alt_labels", []), *extra]

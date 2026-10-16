"""Provenance: every plan item carries a positive graph path and a reason, and the JSON-LD
download parses as RDF with every planned exercise, every exclusion and its rule, and a
connected activity chain. The model is the test double from test_generator."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from coachkg.config import load_settings
from coachkg.generator.intent import Intent
from coachkg.generator.pipeline import GenerateRequest, run
from coachkg.generator.trace import STAGES
from coachkg.skos import iri
from coachkg.world import World, build_world
from tests.test_generator import FakeLLM, _all_offered, _intent

PROV = Namespace("http://www.w3.org/ns/prov#")
CKG = Namespace("urn:coachkg:")
JORDAN = "mbr_01HX9JORDAN"
OTHER = "mbr_01HXGEN0002"

CASES: dict[str, tuple[str, Intent, str]] = {
    "injury": (JORDAN, _intent(injury_mentions=["left knee"]), "Her left knee is bothering her"),
    "no-barbell": (
        OTHER,
        _intent(unavailable_equipment=["Barbell"]),
        "No barbell, only dumbbells and a kettlebell",
    ),
    "exclude-deadlift": (OTHER, _intent(exclusions=["deadlift"]), "Exclude deadlifts"),
}


@pytest.fixture(scope="module")
def world(data_dir: Path) -> World:
    mp = pytest.MonkeyPatch()
    mp.setenv("LLM_MODEL_FAST", "fast-model")
    mp.setenv("LLM_MODEL_MAIN", "main-model")
    try:
        return build_world(load_settings())
    finally:
        mp.undo()


def _plan(world: World, case: str) -> dict[str, Any]:
    member_id, intent, prompt = CASES[case]
    member = world.members[member_id]
    req = GenerateRequest(member_id=member_id, prompt=prompt, minutes=30)

    async def collect() -> list[dict[str, Any]]:
        llm = FakeLLM(intent, _all_offered)
        return [e async for e in run(world, llm, req, member, "coach_01HXSAM")]  # type: ignore[arg-type]

    events = asyncio.run(collect())
    plan: dict[str, Any] | None = next((e["plan"] for e in events if e["event"] == "plan"), None)
    assert plan is not None, events
    return plan


def _items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [i for b in plan["blocks"] for i in b["items"]]


@pytest.mark.parametrize("case", list(CASES))
def test_every_item_has_a_positive_path_and_a_reason(world: World, case: str) -> None:
    plan = _plan(world, case)
    member_id = CASES[case][0]
    items = _items(plan)
    assert items
    for b in plan["blocks"]:
        for i in b["items"]:
            assert i["why"], i["name"]
            assert i["path"], i["name"]
            node = f"ex:{i['exercise_id']}"
            roles = {e["role"] for e in i["path"]}
            assert "block" in roles
            for e in i["path"]:
                assert e["src"] in (node, f"member:{member_id}")
            # Every required item is matched by the member owning it.
            needs = {e["dst"] for e in i["path"] if e["kind"] == "requires"}
            owns = {e["dst"] for e in i["path"] if e["kind"] == "has-equipment"}
            assert needs == owns
            # The ranking split holds: nothing counted against appears as a reason for.
            assert not set(i["why"]) & set(i["counted_against"])
            if b["name"] != "main":
                assert any("programming.yaml" in w for w in i["why"])


def test_injury_plan_paths_show_no_region_was_restricted(world: World) -> None:
    plan = _plan(world, "injury")
    restricted = {r for row in plan["trace"]["restrictions"] for r in row["regions"]}
    assert "region:knee" in restricted
    for i in _items(plan):
        for e in i["path"]:
            if e["kind"] == "stresses" and e["role"] == "region-clear":
                assert e["dst"] not in restricted


def test_no_barbell_plan_never_requires_barbell(world: World) -> None:
    plan = _plan(world, "no-barbell")
    for i in _items(plan):
        assert "equipment:barbell" not in {e["dst"] for e in i["path"] if e["kind"] == "requires"}


def _rdf(plan: dict[str, Any]) -> Graph:
    g = Graph()
    g.parse(data=json.dumps(plan["trace"]["jsonld"]), format="json-ld")
    return g


@pytest.mark.parametrize("case", list(CASES))
def test_jsonld_parses_with_every_exercise_exclusion_and_rule(world: World, case: str) -> None:
    plan = _plan(world, case)
    g = _rdf(plan)
    plan_iri = URIRef(f"urn:coachkg:plan/{plan['id']}")
    assert (plan_iri, RDF.type, PROV.Entity) in g
    assert (plan_iri, RDF.type, CKG.Plan) in g

    # Every planned exercise is an item of the plan, derived from its ranking and its path edges.
    for i in _items(plan):
        ex = iri(f"ex:{i['exercise_id']}")
        items = [s for s in g.subjects(CKG.exercise, ex) if (s, RDF.type, CKG.PlanItem) in g]
        assert len(items) >= 1, i["name"]
        item = items[0]
        assert (plan_iri, PROV.hadMember, item) in g
        derived = set(g.objects(item, PROV.wasDerivedFrom))
        assert any((d, RDF.type, CKG.Ranking) in g for d in derived)
        edges = [d for d in derived if (d, RDF.type, CKG.Edge) in g]
        assert len(edges) == len({(e["src"], e["kind"], e["dst"]) for e in i["path"]})
        for w in i["why"]:
            assert (item, CKG.why, Literal(w)) in g

    # Every exclusion the trace shows is a decision with its exercise, reason and rule or evidence.
    by_name = {str(world.store.node(n)["label"]): n for n in world.store.nodes("exercise")}
    decisions = set(g.subjects(RDF.type, CKG.SafetyDecision))
    excluded = {s for s in decisions if (s, CKG.outcome, Literal("excluded")) in g}
    assert plan["trace"]["excluded"]
    for grp in plan["trace"]["excluded"]:
        for name in grp["exercises"]:
            ex = iri(by_name[name])
            hits = [s for s in excluded if (s, CKG.exercise, ex) in g]
            assert hits, (name, grp["reason"])
            if grp["rule"]:
                rule = URIRef(f"urn:coachkg:rule/{grp['rule']}")
                assert any((s, CKG.rule, rule) in g for s in hits), name
    for s in excluded:
        assert g.value(s, CKG.reason) is not None
        assert set(g.objects(s, PROV.wasDerivedFrom)), s
        for r in g.objects(s, CKG.rule):
            assert (r, RDF.type, CKG.Rule) in g
            assert g.value(r, RDFS.label) is not None


def test_injury_exclusions_carry_their_rule(world: World) -> None:
    plan = _plan(world, "injury")
    g = _rdf(plan)
    ruled = [grp for grp in plan["trace"]["excluded"] if grp["rule"]]
    assert ruled, "expected a contraindication rule to fire for a knee injury"
    for grp in ruled:
        rule = URIRef(f"urn:coachkg:rule/{grp['rule']}")
        assert (rule, RDF.type, CKG.Rule) in g
        assert set(g.subjects(CKG.rule, rule))


def test_activity_chain_is_connected(world: World) -> None:
    plan = _plan(world, "injury")
    g = _rdf(plan)
    base = f"urn:coachkg:plan/{plan['id']}/activity/"
    acts = [URIRef(base + s) for s in STAGES]
    for a in acts:
        assert (a, RDF.type, PROV.Activity) in g
        assert set(g.objects(a, PROV.wasAssociatedWith))
    for prev, nxt in zip(acts, acts[1:], strict=False):
        assert (nxt, PROV.wasInformedBy, prev) in g
        # Something the earlier stage generated is used by the next one.
        generated = set(g.subjects(PROV.wasGeneratedBy, prev))
        assert generated & set(g.objects(nxt, PROV.used)), (prev, nxt)
    plan_iri = URIRef(f"urn:coachkg:plan/{plan['id']}")
    assert (plan_iri, PROV.wasGeneratedBy, acts[-1]) in g


def test_agents_are_roles_and_model_ids_never_appear(world: World) -> None:
    plan = _plan(world, "injury")
    g = _rdf(plan)
    coach = URIRef("urn:coachkg:coach/coach_01HXSAM")
    assert (coach, RDF.type, PROV.Agent) in g
    for role in ("intent-model", "selection-model", "safety-filter"):
        assert (URIRef(f"urn:coachkg:agent/{role}"), RDF.type, PROV.SoftwareAgent) in g
    text = json.dumps(plan["trace"]["jsonld"])
    assert "fast-model" not in text and "main-model" not in text

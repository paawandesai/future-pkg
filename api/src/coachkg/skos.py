"""SKOS export of the concepts the graph reasons over, with their external matches.

Every region, condition, muscle group, movement pattern, equipment item and exercise family
becomes a skos:Concept in one ConceptScheme, with our labels, skos:broader for part-of and is-a,
and skos:*Match links from kg/alignment/ (SNOMED CT by identifier only, Uberon, Wikidata).
Movement patterns have no external match: no openly licensed ontology covers them.

    uv run python -m coachkg.skos > ../kg/export/coachkg-skos.ttl
"""

from __future__ import annotations

import sys
from typing import Any
from urllib.parse import quote

import yaml
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS

from coachkg.alignment import ALIGN_DIR, load_snomed, load_uberon
from coachkg.kg.graph import NetworkXStore

CKG = Namespace("urn:coachkg:")
SCHEME = CKG["scheme"]
KINDS = ("region", "condition", "muscle", "pattern", "equipment", "family")
SNOMED = "http://snomed.info/id/"
UBERON = "http://purl.obolibrary.org/obo/"
WIKIDATA = "http://www.wikidata.org/entity/"
UBERON_SOURCE = URIRef("http://purl.obolibrary.org/obo/uberon.owl")
WIKIDATA_SOURCE = URIRef("https://www.wikidata.org/")
CC_BY_3 = URIRef("https://creativecommons.org/licenses/by/3.0/")
CC0 = URIRef("https://creativecommons.org/publicdomain/zero/1.0/")
RIGHTS = (
    "Concept labels and structure are the future-pkg authors' own, for a synthetic demo. Terms taken "
    "from the Future exercise dataset are not relicensed here. External matches are identifiers only: "
    "SNOMED CT identifiers (no SNOMED CT content is included; SNOMED CT is a registered trademark of "
    "SNOMED International), Uberon IRIs (Uberon, CC BY 3.0) and Wikidata IRIs (CC0)."
)


def load_wikidata() -> list[dict[str, Any]]:
    return list(yaml.safe_load((ALIGN_DIR / "wikidata.yaml").read_text())["alignments"])


def iri(node: str, side: str | None = None) -> URIRef:
    kind, _, rest = node.partition(":")
    tail = f"{kind}/{quote(rest.replace(' ', '_'), safe='')}"
    return CKG[f"{tail}/{side}" if side else tail]


def build(store: NetworkXStore) -> Graph:
    g = Graph()
    g.bind("skos", SKOS)
    g.bind("dcterms", DCTERMS)
    g.add((SCHEME, RDF.type, SKOS.ConceptScheme))
    g.add((SCHEME, SKOS.prefLabel, Literal("Coach knowledge graph concepts", lang="en")))
    g.add((SCHEME, DCTERMS.source, Literal("Future exercise dataset and kg/rules (synthetic demo)")))
    # Rights: our labels and structure; dataset-derived terms are not relicensed; external matches
    # are identifiers, credited with their sources' licences.
    g.add((SCHEME, DCTERMS.rights, Literal(RIGHTS, lang="en")))
    for source, licence in ((UBERON_SOURCE, CC_BY_3), (WIKIDATA_SOURCE, CC0)):
        g.add((SCHEME, DCTERMS.source, source))
        g.add((source, DCTERMS.license, licence))
    for kind in KINDS:
        top = CKG[f"{kind}s"]
        g.add((top, RDF.type, SKOS.Collection))
        g.add((top, SKOS.prefLabel, Literal(f"{kind}s", lang="en")))
        for n in store.nodes(kind):
            d = store.node(n)
            c = iri(n)
            g.add((c, RDF.type, SKOS.Concept))
            g.add((c, SKOS.inScheme, SCHEME))
            g.add((c, SKOS.prefLabel, Literal(str(d.get("label", n)), lang="en")))
            for alt in d.get("alt_labels") or []:
                g.add((c, SKOS.altLabel, Literal(str(alt), lang="en")))
            g.add((top, SKOS.member, c))
    for kind in ("part-of", "is-a"):
        for e in store.all_edges():
            if e.kind == kind:
                g.add((iri(e.src), SKOS.broader, iri(e.dst)))

    def match(concept: str, how: str, target: str, side: str | None = None, label: str = "") -> None:
        c = iri(concept, side)
        if side:
            g.add((c, RDF.type, SKOS.Concept))
            g.add((c, SKOS.inScheme, SCHEME))
            g.add((c, SKOS.broader, iri(concept)))
            g.add((c, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((c, SKOS[how], URIRef(target)))

    for s in load_snomed():
        match(s["concept"], s["match"], SNOMED + s["sctid"], s.get("side"), s["our_label"])
    for u in load_uberon():
        match(u["concept"], u["match"], UBERON + u["uberon"].replace(":", "_"))
    for w in load_wikidata():
        match(w["concept"], w["match"], WIKIDATA + w["wikidata"])
    return g


if __name__ == "__main__":
    from coachkg.config import load_settings
    from coachkg.data import load_exercises
    from coachkg.kg.graph import build_movement_graph
    from coachkg.kg.rules import load_rules

    settings = load_settings()
    catalog = load_exercises(settings.data_dir)
    store = build_movement_graph(catalog, load_rules(settings.kg_dir, catalog))
    sys.stdout.write(build(store).serialize(format="turtle"))

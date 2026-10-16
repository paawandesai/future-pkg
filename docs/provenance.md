# Provenance (PROV-O)

Every drafted plan carries a full provenance record of the run that produced it, as
[PROV-O](https://www.w3.org/TR/prov-o/) in JSON-LD. The server builds it
(`api/src/coachkg/generator/trace.py`, `prov_document`), stores it with the plan under
`trace.jsonld`, and the generator page's **Download trace (JSON-LD)** button saves exactly that
document. Nothing in it is written by a model: every record restates a resolver result, a safety
filter decision, a scoring rule or the assembler's output.

This is coach decision support. The record explains why the draft looks the way it does. It does
not certify a workout, and the coach still confirms every plan.

## Why PROV-O

The brief asks for a trace of why each exercise was chosen, which graph path justified it and
what was filtered out. PROV-O already has the three things that answer this: activities (the
pipeline stages), entities (the request, the readings, the decisions, the plan and its items) and
agents (who or what acted). Using the W3C vocabulary means the download loads into any RDF tool
and can be joined with the SKOS export (`kg/export/coachkg-skos.ttl`), because both use the same
IRIs for graph concepts.

## IRIs and vocabulary

| Thing | IRI | Notes |
|---|---|---|
| Graph concept | `urn:coachkg:<kind>/<id>` | Same scheme as `coachkg.skos.iri`, e.g. `urn:coachkg:region/knee`, `urn:coachkg:ex/<exercise id>`, `urn:coachkg:member/<member id>` |
| Graph edge | `urn:coachkg:edge/<kind>/<src>/<dst>` | Node ids percent-encoded. `from`, `to`, `edgeKind`, plus `edgeProv` (dataset, signed or model) and `edgeSource` when the safety filter used it as evidence |
| Rule | `urn:coachkg:rule/<rule id>` | `rdfs:label` is the rule's paraphrase, `file` the rule file, `condition` the condition concept, `citation` a DOI link or dataset name |
| Plan | `urn:coachkg:plan/<plan id>` | Plan-scoped records hang under it: `/activity/<stage>`, `/request`, `/intent`, `/reading/<n>`, `/restriction/<n>`, `/decision/<n>`, `/candidates`, `/score/<exercise id>`, `/selection`, `/item/<block>/<n>` |
| Agent | `urn:coachkg:coach/<coach id>`, `urn:coachkg:agent/<role>` | The coach is a `prov:Person`. Model roles and deterministic components are `prov:SoftwareAgent`s |

Terms that are not PROV-O live under the `coachkg:` prefix (`urn:coachkg:`): classes `Plan`,
`PlanItem`, `Ranking`, `Selection`, `CandidateSet`, `SafetyDecision`, `Restriction`, `Reading`,
`Rule`, `Edge`, and properties such as `exercise`, `outcome`, `reason`, `rule`, `why`,
`countedAgainst`, `block`, `sets`, `reps`. The `@context` is inline in the document, so no network
fetch is needed to expand it.

## The activity chain

One `prov:Activity` per stage, each `prov:wasInformedBy` the one before it and each using an
entity the previous one generated:

```
read-request ──▶ resolve ──▶ safety-filter ──▶ score ──▶ select ──▶ assemble
  used request    used intent  used readings,    used       used       used selection,
  coach +         + graph      member, graph,    candidates rankings   programming.yaml
  intent-model                 rules             scorer     selection- assembler
                               safety-filter                model
  ─▶ intent       ─▶ readings  ─▶ restrictions,  ─▶ rankings ─▶ selection ─▶ plan + items
                                 decisions,
                                 candidate set
```

Agents are named by role, never by model id: `intent-model`, `selection-model`, `resolver`,
`safety-filter`, `scorer`, `assembler`. The model ids stay in configuration (`LLM_MODEL_FAST`,
`LLM_MODEL_MAIN`). Activities that called a model also carry `elapsedMs` and token counts.

What links to what:

- **Plan item** `prov:wasDerivedFrom` its ranking (the `why` and `countedAgainst` lines), the
  selection, and every edge on its positive path:
  - `ex requires equipment` with `member has-equipment equipment` for each item it needs;
  - `ex stresses region` for each region it loads, marked not restricted, or coach-cleared when a
    low-impact clearance applied;
  - the focus edges (`has-pattern`, `targets`, `variant-of`) when the request named a focus;
  - the `has-pattern` edges that placed it in its block. Warm-up and cool-down placement comes
    from the block patterns in `kg/rules/programming.yaml`.
- **Safety decision** (excluded, downranked or flagged) names its `exercise`, `outcome` and
  `reason`. It `prov:wasDerivedFrom` its evidence edges (`requires`, `stresses`, `variant-of`,
  `contraindicated-for`), its rule when one fired, and the restrictions when it loads a
  restricted region. An exercise the request excluded by name derives from the request readings.
- **Restriction** derives from the member record (an injury on file) or from the request
  readings.
- **Plan** `prov:hadMember` its items, records `status` (always `draft` when generated) and
  `awaitsConfirmationBy` the coach, and lists any `unverified` lines.

Request text is not repeated on the request entity. The readings quote only the phrases the
resolver matched, as the on-screen trace already does.

## Excerpt

Abridged from a knee-injury plan (`…` replaces the plan and exercise ids):

```json
{
  "@context": { "prov": "http://www.w3.org/ns/prov#", "coachkg": "urn:coachkg:", "…": "…" },
  "@graph": [
    {
      "@id": "urn:coachkg:plan/…/activity/safety-filter",
      "@type": "prov:Activity",
      "stage": "safety-filter",
      "used": ["urn:coachkg:plan/…/reading/0", "urn:coachkg:member/mbr_01HX9JORDAN",
               "urn:coachkg:graph/movement", "urn:coachkg:rule/pfp-no-deep-loaded-knee-flexion"],
      "wasAssociatedWith": ["urn:coachkg:agent/safety-filter"],
      "wasInformedBy": "urn:coachkg:plan/…/activity/resolve"
    },
    {
      "@id": "urn:coachkg:plan/…/decision/8",
      "@type": ["prov:Entity", "coachkg:SafetyDecision"],
      "wasGeneratedBy": "urn:coachkg:plan/…/activity/safety-filter",
      "exercise": "urn:coachkg:ex/…",
      "outcome": "flagged",
      "reason": "Kneeling puts direct pressure on the front of the knee; ask the member how it feels.",
      "rule": "urn:coachkg:rule/pfp-kneeling-flag",
      "wasDerivedFrom": ["urn:coachkg:edge/contraindicated-for/ex%3A…/condition%3Apatellofemoral_pain",
                         "urn:coachkg:rule/pfp-kneeling-flag"]
    },
    {
      "@id": "urn:coachkg:plan/…/item/warmup/0",
      "@type": ["prov:Entity", "coachkg:PlanItem"],
      "wasGeneratedBy": "urn:coachkg:plan/…/activity/assemble",
      "wasDerivedFrom": ["urn:coachkg:plan/…/score/…", "urn:coachkg:plan/…/selection",
                         "urn:coachkg:edge/stresses/ex%3A…/region%3Acervical_spine",
                         "urn:coachkg:edge/has-pattern/ex%3A…/pattern%3Amobility%20-%20dynamic"],
      "exercise": "urn:coachkg:ex/…",
      "label": "Standing Neck Circles",
      "block": "warmup",
      "why": ["needs no equipment", "loads cervical spine, which is not restricted",
              "mobility - dynamic is a warm-up pattern in programming.yaml"]
    }
  ]
}
```

## Loading the download

```python
from rdflib import Graph, Namespace
from rdflib.namespace import RDF

PROV = Namespace("http://www.w3.org/ns/prov#")
CKG = Namespace("urn:coachkg:")

g = Graph()
g.parse("trace-<plan id>.jsonld", format="json-ld")   # rdflib 6+ reads JSON-LD natively

# Planned exercises and the graph edges behind each one.
for item in g.subjects(RDF.type, CKG.PlanItem):
    edges = [d for d in g.objects(item, PROV.wasDerivedFrom) if (d, RDF.type, CKG.Edge) in g]
    print(g.value(item, CKG.block), g.value(item, CKG.exercise), len(edges))

# Exclusions and the rule behind each.
q = """
PREFIX ckg: <urn:coachkg:>
SELECT ?exercise ?reason ?rule WHERE {
  ?d a ckg:SafetyDecision ; ckg:outcome "excluded" ; ckg:exercise ?exercise ; ckg:reason ?reason .
  OPTIONAL { ?d ckg:rule ?rule }
}"""
for row in g.query(q):
    print(row.exercise, row.reason, row.rule)
```

To join with concept labels and external matches, also load `kg/export/coachkg-skos.ttl` into the
same graph: exercise families, regions, equipment, patterns and conditions share IRIs.

`api/tests/test_provenance.py` parses the document with rdflib for an injury plan, a no-barbell
plan and an exclude-deadlift plan. It checks that every planned exercise, every exclusion and its
rule appear as triples, that the six activities form a connected chain, and that no model id
appears.

Plans saved before this change only have the safety filter's records (`trace.prov`). The page
still downloads those, wrapped with the PROV prefix only.

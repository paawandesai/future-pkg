# Ontology alignment

Our graph is hand-rolled. External ontologies give it stable identifiers and a way to check our
anatomy, not safety logic. Each alignment lives in `kg/alignment/` and is checked live in CI.

## What we pulled and why

| Source | Licence | What we use | Where |
|---|---|---|---|
| SNOMED CT (via NCI EVS) | SNOMED International Affiliate licence; reference only here | 21 codes for the joints and conditions the safety filter reasons about, with sided codes for knee, hip and ankle | `kg/alignment/snomed.yaml` |
| Uberon | CC BY 3.0 | 17 IRIs for our anatomy regions and 19 for the dataset's muscle groups, with their labels | `kg/alignment/uberon.yaml` |
| Wikidata | CC0 | 23 items for equipment (exact, close, broad or related matches) | `kg/alignment/wikidata.yaml` |

SNOMED entries hold the code, our own label, the SKOS match type and a SHA-256 of the name EVS
returned when the code was pinned. No SNOMED descriptions, synonyms, hierarchy or relationships
are stored. `api/tests/test_snomed_live.py` resolves every code at `api-evsrest.nci.nih.gov`,
fails on a 404, an inactive concept or a changed name, and writes `prov:wasDerivedFrom`
evidence (retrieval time, response hash, terminology version) to `.cache/evs/`, which is not
committed.

Codes were found by searching EVS on 2026-10-15; none came from memory or a model. Notes from
that search:

- Knee joint `49076000` reports `leaf: true` while it has children. EVS children are is-a
  relations, not part-of, so we never use them to build our part-of tree. Explore with
  `/descendants`, and keep is-a and part-of as separate edges.
- Laterality is explicit: left knee `719442003`, right knee `719443008` (likewise hip and ankle).
  "Left knee" in a request maps to the left-sided code, never to plain "knee".
- The general patellofemoral pain concept is `430725003`. Side-specific codes found in the
  search come from a national extension, so we don't use them.
- Shoulder and cervical spine are `closeMatch`: SNOMED's nearest structure concepts are broader or
  narrower than our region.

Uberon and Wikidata entries were also found by live search (EBI OLS and the Wikidata API) on
2026-10-15, and `test_uberon_live.py` and `test_wikidata_live.py` check each one still carries the
recorded label. Most muscle groups are `closeMatch`, because the dataset's groups ("quads",
"upper back") are coarser than Uberon's muscles. Ten equipment items are left unmapped and the
reason for each is in the file.

## SKOS export

`kg/export/coachkg-skos.ttl` is one `skos:ConceptScheme` covering every region, condition,
muscle group, movement pattern, equipment item and family in the graph: our labels, `skos:broader`
from part-of and is-a, sided sub-concepts for the sided SNOMED codes, and every `skos:*Match`
above. Regenerate it with `cd api && uv run python -m coachkg.skos > ../kg/export/coachkg-skos.ttl`;
a test fails when it drifts from the graph. Movement patterns (37) have no external match: no
openly licensed ontology covers training movement patterns, and the closest work (COPPER, OPE) is
cite-only for the reasons below.

## What each suggested ontology gives us, and what we took

| Ontology | What it offers, by its own description | What we use | What we left out, and why |
|---|---|---|---|
| **SNOMED CT** (via NCI EVS) | Clinical anatomy, joints, disorders and injuries with stable codes | Identifiers for our 18 regions and 5 conditions (`snomed.yaml`), live-checked in CI. Our `part-of` hierarchy mirrors its anatomy for the parts we need, so "knee" covers its sub-structures. | Descriptions and the rest of the hierarchy: redistribution needs a licence, and a hand-picked hierarchy of 18 regions is easier to review and sign than a slice of 350,000 concepts. |
| **OPE** (Ontology of Physical Exercises) | Exercise types, the musculoskeletal system, equipment and injuries | Its split of the domain into exercise, body structure, equipment and injury is the shape of KG1's node types. | Classes and terms: no licence is published, it is an alpha release, and its OWL import fails, so nothing can be redistributed or kept in sync. The dataset's own taxonomy plus Uberon and Wikidata cover the same ground with clear licences. |
| **COPPER** | Personalisation and behaviour-change concepts for activity recommendations (barriers, motivation, context, goals) | The idea that a recommendation depends on where the member is in their journey: our journey-stage rule (tenure, falling adherence) and the churn reasons are the two places this shows. | Its classes: CC BY-NC is a non-commercial licence, which our licence policy rules out. If Future licensed it, its behaviour-change concepts would be the natural home for KG2's goals, preferences and adherence nodes. |
| **PROV-O** | Activities, entities, agents and derivation | The whole plan trace ([provenance.md](provenance.md)): one activity per stage, coach and model roles as agents, every exclusion linked to its rule and evidence. | Nothing: it is a W3C standard, small, and exactly the "why was this chosen" record the brief asks for. |
| **SKOS** | Concept schemes, labels and mappings | Every catalog term as a concept with our labels and coach shorthand, `broader` from part-of and is-a, and `exact/close/broad/relatedMatch` to SNOMED, Uberon and Wikidata (`kg/export/coachkg-skos.ttl`). | OWL reasoning: we don't need inference, and SKOS keeps the mapping reviewable. |

## What we left out

- **SNOMED content** beyond identifiers: redistributing descriptions needs a licence we don't hold.
- **COPPER** (CC BY-NC 4.0) and **OPE** (no licence, alpha, broken import): cited as design
  influences only. No classes, labels or definitions copied.
- **UMLS** (no redistribution, bundles SNOMED), **FMA** (licence statements conflict), **RadLex**,
  **CPT**: not used.

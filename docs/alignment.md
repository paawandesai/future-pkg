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

## What we left out

- **SNOMED content** beyond identifiers: redistributing descriptions needs a licence we don't hold.
- **COPPER** (CC BY-NC 4.0) and **OPE** (no licence, alpha, broken import): cited as design
  influences only. No classes, labels or definitions copied.
- **UMLS** (no redistribution, bundles SNOMED), **FMA** (licence statements conflict), **RadLex**,
  **CPT**: not used.

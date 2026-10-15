# Ontology alignment

Our graph is hand-rolled. External ontologies give it stable identifiers and a way to check our
anatomy, not safety logic. Each alignment lives in `kg/alignment/` and is checked live in CI.

## What we pulled and why

| Source | Licence | What we use | Where |
|---|---|---|---|
| SNOMED CT (via NCI EVS) | SNOMED International Affiliate licence; reference only here | 21 codes for the joints and conditions the safety filter reasons about, with sided codes for knee, hip and ankle | `kg/alignment/snomed.yaml` |
| Uberon | CC BY 3.0 | 17 IRIs and their labels for our anatomy regions | `kg/alignment/uberon.yaml` |

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

## What we left out

- **SNOMED content** beyond identifiers: redistributing descriptions needs a licence we don't hold.
- **COPPER** (CC BY-NC 4.0) and **OPE** (no licence, alpha, broken import): cited as design
  influences only. No classes, labels or definitions copied.
- **UMLS** (no redistribution, bundles SNOMED), **FMA** (licence statements conflict), **RadLex**,
  **CPT**: not used.

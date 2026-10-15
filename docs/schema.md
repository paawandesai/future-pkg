# Graph schema

## Movement / clinical graph (KG 1)

| Node kind | Id form | From |
|---|---|---|
| exercise | `ex:<id>` | `exercises.json` rows, plus `kg/authored/exercises.yaml` (origin `authored`) |
| muscle | `muscle:<name>` | dataset `muscle_groups` |
| pattern | `pattern:<name>` | dataset `movement_patterns` |
| equipment | `equipment:<name>` | dataset `equipment_required` |
| region | `region:<id>` | `kg/rules/anatomy.yaml` |
| family | `family:<id>` | `kg/rules/families.yaml` |
| condition | `condition:<id>` | `kg/rules/contraindications.yaml` |

| Edge | From → to | Meaning | Source |
|---|---|---|---|
| `targets` | exercise → muscle | works this muscle group | dataset |
| `has-pattern` | exercise → pattern | follows this movement pattern | dataset |
| `requires` | exercise → equipment | needs all listed equipment | dataset |
| `stresses` | exercise → region (`laterality`: left/right/both) | loads this joint or region | dataset `joints_loaded` + `side`; `exercise_attributes.yaml` for documented gaps |
| `part-of` | region → region | anatomical containment (never is-a) | `anatomy.yaml` |
| `variant-of` | exercise → family | is a variation of | `families.yaml` |
| `is-a` | family → family | family hierarchy | `families.yaml` |
| `affects` | condition → region | where a condition sits | `contraindications.yaml` |
| `contraindicated-for` | exercise → condition (`rule`, `effect`, `via`) | excluded or flagged while the condition is active; materialised from each rule at build time, cited as the decision's evidence | `contraindications.yaml` |
| `substitutes-for` | equipment → equipment (`patterns`) | can stand in for, for these patterns only | `equipment.yaml` |

Every edge has `prov` (`dataset`, `model` or `human:<initials>`) and `source`. Readers that make
safety decisions request trusted edges only (`dataset` or `human:*`).

Laterality: the catalog's unilateral rows are all left-side (`left_leg`, `left_arm`,
`left_side`) and their `bilateral_pair_id` points at rows the file does not contain. We keep
those ids as unresolved references and never invent right-side rows. A row with no `side` loads
both sides.

Exercise nodes also carry attributes from `exercise_attributes.yaml` (`loaded_knee_flexion`,
`impact`, `kneeling`) with the file's attribution.

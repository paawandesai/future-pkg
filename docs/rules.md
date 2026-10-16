# Rule files and how they are signed

The safety filter may act only on facts from the dataset or from rules a person has signed.
Everything Claude drafted starts as `model`-attributed and is ignored by the filter until signed.

| File | What it holds | Used for safety? |
|---|---|---|
| `kg/rules/anatomy.yaml` | Body regions, part-of tree, laterality, links to dataset joints | Yes (region expansion) |
| `kg/rules/exercise_attributes.yaml` | Loaded knee-flexion band, impact level, kneeling, missing joint loads | Yes |
| `kg/rules/contraindications.yaml` | Conditions and exclude/flag rules with citations | Yes |
| `kg/rules/families.yaml` | Exercise families (`variant-of`) and family hierarchy (`is-a`) | Yes (exclusion requests) |
| `kg/authored/exercises.yaml` | Exercises we wrote as structured fields | Yes (their joint loads) |
| `kg/rules/equipment.yaml` | Equipment substitutes | No, ranking only |
| `kg/rules/muscle_actions.yaml` | Muscle group to joint actions | No, explanations only |
| `kg/rules/recovery.yaml` | Self-administered recovery and referral roles | No |
| `kg/rules/programming.yaml` | Default sets, reps, rest, tempo and warm-up/cool-down patterns | No, plan assembly only |

## Signing a file

A reviewer reads the file and, if they agree, changes its `review` block:

```yaml
review:
  status: signed
  drafted_by: model
  reviewer: PD          # initials
  signed_on: 2026-10-16
```

The loader refuses `status: signed` without initials and a date. Once signed, every edge from
that file is attributed to `human:<initials>` in the graph and in provenance traces.

## Per-rule evidence

Inside `contraindications.yaml`, a signed file is still not enough: each rule needs at least one
checked source before the filter uses it. A dataset field (for example the coach's injury note in
`member-context.json`) counts as checked. A paper counts once its DOI has been checked against
Crossref (`doi_checked`) and its claim has been checked on the source (`claim_checked`). A rule
without a checked source is skipped and the plan is marked "unverified".

## What happens while files are unsigned

Unsigned facts may make the filter stricter, never looser:

- A fact from an unsigned file can exclude or flag an exercise (for example the extra knee load
  on Jumping Jack). Each such use is listed under "unverified" in the plan, with the reason.
- Allowing an exercise needs dataset facts or signed facts. Exercises whose joint loads come only
  from unsigned files (the authored exercises) are not offered as candidates.
- A coach's low-impact clearance relaxes knee loading only for exercises whose attributes come
  from a signed file. Deep loaded knee flexion and high impact stay excluded even then.
- Injury regions that cannot be linked to a dataset joint through trusted edges block drafting and
  ask the coach to confirm the region (fail closed).
- Programming defaults (`programming.yaml`) are not safety facts. The file is signed (PD,
  2026-10-16). If it is set back to draft, every plan says its sets, reps and rest are
  model-drafted defaults for the coach to adjust.

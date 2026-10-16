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

## Member context graph (KG 2)

One graph per member, built at startup from that member's record
(`api/src/coachkg/kg/member_graph.py`). Every field family of the record is ingested. The
copilot's read-only tools (`copilot/data.py`) answer by querying this graph, not the raw JSON; the
server picks the graph from the signed-in coach and the URL, so no tool can reach another member.

| Node kind | Id form | From | Notes |
|---|---|---|---|
| member | `member:<id>` | `profile` | age, sex, height, weight, timezone, member since, coach id, tier; `adherence_trend`; `fictional: true` |
| goal | `goal:<id>` | `goals` | text, priority, `target_date` |
| preferences | `preferences:<id>` | `preferences` | session minutes, days per week, preferred days, notes (as recorded) |
| dislike | `dislike:<n>` | `preferences.dislikes` | the recorded text |
| equipment_unresolved | `equipment-unresolved:<n>` | `equipment_available` | only for items that don't match a KG 1 equipment node |
| injury | `injury:<id>` | `injuries` | region text, joint, status, severity, `date` = onset, notes, `active` |
| session | `session:<date>` | `workout_history` | `date`, title, planned, completed, minutes, RPE, the exercise names as recorded |
| adherence_week | `adherence:<week_of>` | `adherence.weekly_completion_pct` | `date` = week start as recorded, `pct` |
| biomarker | `biomarker:resting_hr_bpm`, `biomarker:hrv_ms` | `biomarkers` | value and unit; the record gives no date, so `date` is null and the value is reported as of AS_OF |
| sleep_night | `sleep:<date>` | `biomarkers.sleep_hours_last_7_days` | hours; `date_assigned: true` (the file has no night dates: we count back from AS_OF) |
| weight_reading | `weight:<date>` | `biomarkers.weight_trend_kg` | kg |
| lab_panel | `lab-panel:<panel>` | `labs.blood_panel`, `labs.dexa_scan` | panel name and `date` |
| lab_value | `lab-value:<panel>:<name>` | each value in a panel | name, value and date only: no ranges, flags or derived nodes |
| message | `message:<n>` | `chat_history` | `ts`, `date`, `provenance` (`member-said` or `coach-said`), the quote |
| attachment | `attachment:<n>:<m>` | `chat_history[].attachments` | type and caption only (the dataset has no image bytes); carries the message's provenance |
| coach_brief | `brief:<generated_for>` | `coach_brief` | `date` = the day it was generated for |
| morning_task | `task:<n>` | `coach_brief.morning_tasks` | type and text, as written |
| churn_claim | `claim:churn` | `coach_brief.churn_risk` | the brief's level and reasons. It is what the brief *claims*; our own score is computed separately and shown next to it |

| Edge | From → to | Meaning | prov |
|---|---|---|---|
| `has-goal` | member → goal | a goal on the record | dataset |
| `concerns` | goal → KG 1 region | a body region the goal names | dataset |
| `has-preferences` | member → preferences | | dataset |
| `dislikes` | member → dislike | | dataset |
| `refers-to` | dislike → KG 1 family, exercise or pattern (`match`) | what the dislike names, via the resolver | dataset |
| `has-equipment` | member → KG 1 equipment (`as_recorded`) | owns this equipment | dataset |
| `has-equipment-unresolved` | member → equipment_unresolved | owns something we couldn't match | dataset |
| `has-injury` | member → injury | | dataset |
| `located-at` | injury → KG 1 region | where the injury is | dataset |
| `scheduled` | member → session | a planned or completed session | dataset |
| `included` | session → KG 1 exercise (`as_recorded`, `position`, `match`) | an exercise done in that session | dataset |
| `has-adherence` | member → adherence_week | weekly completion | dataset |
| `has-biomarker` | member → biomarker | | dataset |
| `slept` | member → sleep_night | | dataset |
| `has-weight` | member → weight_reading | | dataset |
| `has-lab-panel` | member → lab_panel | | dataset |
| `has-value` | lab_panel → lab_value | | dataset |
| `sent` / `received` | member → message | a message from / to the member | member-said / coach-said |
| `has-attachment` | message → attachment | | the message's provenance |
| `mentions` | message → KG 1 region or condition | a body word in the message, found by the resolver's scan | the message's provenance |
| `has-brief` | member → coach_brief | the provided brief | dataset |
| `has-task` | coach_brief → morning_task | | dataset |
| `claims` | coach_brief → churn_claim (`asserted_by`) | the brief asserts this churn level | dataset |

Every dated fact is its own node with a `date` (sessions, adherence weeks, sleep nights, weight
readings, lab panels and values, messages, injuries, the brief). Login events are not in KG 2: they
are generated demo data (`fixtures/generated-login-events.json`) and stay separate so every answer
that uses them can say so.

### How KG 1 and KG 2 join

The two graphs share concept nodes: KG 2 copies the KG 1 node with the same id, so a query can
cross from one to the other.

- **Injury → region.** `injury:<id> -located-at-> region:<id>`. The safety filter walks KG 1 from
  that region (`part-of`, `stresses`, `affects`, `contraindicated-for`); the filter resolves the
  same region from the record itself and never reads KG 2 chat edges.
- **Owned equipment → equipment.** `member -has-equipment-> equipment:<name>`, the same node KG 1
  exercises point at with `requires`.
- **Session exercises → exercises.** `session -included-> ex:<id>` when the recorded name resolves
  (exact or fuzzy, recorded in `match`); unresolved names stay on the session as recorded.
- **Dislikes → families, exercises or patterns.** `dislike -refers-to-> family:deadlift`, which KG 1
  links to its variants with `variant-of`.
- **Messages and goals → regions.** `mentions` and `concerns` edges point at KG 1 regions or
  conditions.

Member text never becomes a trusted fact: `mentions` edges carry `member-said` or `coach-said`
provenance, and the safety filter reads only `dataset` and `human:*` edges. A message can raise
something for the coach to review; only the coach's structured clearance changes a restriction.

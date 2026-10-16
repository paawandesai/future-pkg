# Roadmap: more exercises and connections

This is planned work, not built. The graph today has 56 exercises (50 from the dataset, 6
authored) and 532 edges. Only one edge kind (`variant-of`) links an exercise to anything like
another exercise, so alternatives come from shared patterns and muscles alone, and a strict
restriction leaves few main-block options (with the left-knee scenario, 45-minute plans stop at
about 35 minutes).

Decisions taken (2026-10-16, reviewer PD):

- Submit the current build as it is. This document is the roadmap.
- Grow the catalog to about 200 exercises, written by us as our own data.
- Leave wger's share-alike data out (it would make the catalog CC BY-SA). Its 21 CC0 entries
  may be imported.
- Add hypertension, osteoporosis and shoulder impingement as condition rules, and pregnancy as
  caution flags only.
- Condition rules may get a second reviewer with clinical training before they are signed.

## Where new exercises come from

Exercise names and facts (pattern, equipment, muscles) aren't copyrightable; instructions and
images are, so we copy neither.

| Source | Use |
| --- | --- |
| [wger](https://wger.de/api/v2/license/) | The 21 CC0 entries only. The other 911 are CC BY-SA. |
| [free-exercise-db](https://github.com/yuhonas/free-exercise-db) | A checklist of which exercises exist. Copy nothing: its images and probably its text [came from a commercial site](https://github.com/yuhonas/free-exercise-db/issues/2). |
| Wikidata (CC0) | Cross-links and labels. |
| [EXMO](https://github.com/Exercise-Medicine-Ontology/EXMO) (CC BY 4.0) | Upper-level classes. |
| Uberon (CC BY 3.0) | Finer muscle targets than today's 19 groups. |
| [Compendium of Physical Activities](https://pacompendium.com/) | MET values for conditioning work, cited and unchanged. |
| ExerciseDB, API Ninjas, ACE, ExRx | Not used: proprietary or terms forbid reuse. |

The catalog's backbone is ACSM's classification (single or multi-joint, large or small muscle;
[2009](https://doi.org/10.1249/mss.0b013e3181915670) and
[2026](https://doi.org/10.1249/mss.0000000000003897) position stands) with the movement-pattern
families coaches share (Dan John's fundamentals, the anti-movement core model, Boyle and Cressey's
single-leg classes, Cook's postural progression). Proprietary frameworks (NSCA, NASM, FMS) are
cited and paraphrased, never copied.

## New edges between exercises

All six are ranking and layout only. None can make an excluded exercise allowed.

| Edge | Example | Effect | Evidence |
| --- | --- | --- | --- |
| `progression-of` / `regression-of`, with a lever (load, lever arm, base, stability, range, tempo, unilateral) | knee push-up → push-up → feet-elevated push-up | Easier version under a restriction or for a new member; harder when completion is high | [Ebben 2011](https://pubmed.ncbi.nlm.nih.gov/21873902/), [Calatayud 2017](https://pubmed.ncbi.nlm.nih.gov/28157133/), [McGill 2009](https://pubmed.ncbi.nlm.nih.gov/19154838/); expert consensus for squat and hinge |
| `lower-knee-load-than` | short lunge → step lunge → deep lunge | Lowest-load version for a knee restriction | [Escamilla 2022](https://pubmed.ncbi.nlm.nih.gov/35697336/), [Escamilla 2009](https://pubmed.ncbi.nlm.nih.gov/19276845/) |
| `pairs-with` (agonist-antagonist) | dumbbell bench press + chest-supported row | Two exercises per block to fit more work in the window | [Robbins 2010](https://pubmed.ncbi.nlm.nih.gov/20847705/), [Paz 2017](https://pubmed.ncbi.nlm.nih.gov/28933712/) |
| `warms-up-for` | hip airplane before split squat | Warm-up items that prepare the main block | [Thorborg 2017](https://pubmed.ncbi.nlm.nih.gov/28087568/), [Behm 2016](https://pubmed.ncbi.nlm.nih.gov/26642915/) |
| `primes` (contrast pair) | heavy squat then jump squat | Advanced members only, flagged | [Seitz and Haff 2016](https://pubmed.ncbi.nlm.nih.gov/26508319/), [Blazevich 2019](https://pubmed.ncbi.nlm.nih.gov/31736781/) |
| `bilateral-pair-of` | left-side row → right-side row | Fixes the 18 left-only rows | Dataset structure |

Two findings shape these edges: squat depth isn't a simple knee-load ladder, because kneecap load
peaks near 90 degrees ([Hartmann 2013](https://pubmed.ncbi.nlm.nih.gov/23821469/)), and exercise
order should follow the session's priority ([Simão 2012](https://pubmed.ncbi.nlm.nih.gov/22292516/)).

## New conditions

| Condition | Proposed effect | Sources |
| --- | --- | --- |
| Hypertension | Flag heavy sets to failure; favour submaximal isometrics | [Edwards 2023](https://pubmed.ncbi.nlm.nih.gov/37491419/), [MacDougall 1985](https://pubmed.ncbi.nlm.nih.gov/3980383/) |
| Osteoporosis | Exclude loaded spinal flexion; prefer hinge, balance and back-extensor work | [Beck 2017](https://pubmed.ncbi.nlm.nih.gov/27840033/), [Giangregorio 2015](https://pubmed.ncbi.nlm.nih.gov/25510579/) |
| Shoulder impingement signs | Flag raises above 90 degrees and thumb-down raises | [Escamilla 2009](https://pubmed.ncbi.nlm.nih.gov/19769415/), [Kolber 2014](https://pubmed.ncbi.nlm.nih.gov/24077379/) |
| Pregnancy | Caution flag on lying-on-back work later in pregnancy, never an exclusion | [Mottola 2019](https://pubmed.ncbi.nlm.nih.gov/30337348/) |

Low back pain and knee or hip osteoarthritis get no bans: the evidence supports exercise, not
exclusions ([Hayden 2021](https://pubmed.ncbi.nlm.nih.gov/34580864/),
[OARSI 2019](https://pubmed.ncbi.nlm.nih.gov/31278997/)). Hip impingement and lateral elbow pain
are left out; the evidence is too weak for a rule.

## Phases

1. **Foundations.** Schema for the six edge kinds, provenance and evidence tier on every node
   and edge, right-side twins. Sign-off: schema and twins.
2. **Catalog to about 200.** Each new exercise needs `stresses`, equipment and muscle edges
   before it can be a candidate; rows without loading data stay out (fails closed). Sign-off:
   the authored exercise file.
3. **Connections.** Progressions, knee-load order, pairings and warm-up links, used by the
   generator for ranking and block layout. Sign-off: the link files.
4. **New conditions.** The only phase that changes what the safety filter excludes. Each
   condition gets a test that no excluded exercise reaches a plan, and an eval scenario.
   Sign-off: the condition rules, ideally by a second, clinically trained reviewer.

The existing rules hold throughout: a model never writes edges, unsigned files can only
restrict, and a rule without a checked citation shows as "unverified".

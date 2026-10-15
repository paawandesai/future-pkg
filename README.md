# future-pkg: knowledge-graph coach dashboard

> **Demo — synthetic data only.** Every member in this project is fictional.

Coach decision support for personal-training coaches. It does two things:

1. **Drafts a workout** from a coach's request ("45 minutes, lower body, her left knee is still a bit
   sore"). It uses a knowledge graph of exercises, anatomy and the member's context. Every choice
   has a provenance trace, and the draft waits for the coach to confirm it.
2. **Answers questions about a member** in a copilot with read-only tools. It returns charts, a
   churn signal with its reasons, and a congratulation message the coach can copy but never send
   from here.

It is not medical advice. It never decides that a workout is safe. The coach confirms every plan.

**Deployed demo:** https://d1221xkl4z96di.cloudfront.net. Accounts are invite-only (Cognito):
anyone can request one from the sign-in page, and an admin approves each request on the Admin
page before Cognito emails an invite. Plans are purged daily. See [docs/deploy.md](docs/deploy.md).

The demo coach has six fictional members. Jordan comes from the assessment data; five more are
generated (`scripts/generate_fixtures.py`) to show different cases:

| Member | Case |
|---|---|
| Priya Nair | Active right-shoulder tendinopathy: shoulder work is excluded until the coach records a clearance |
| Marcus Bell | Only a mat and a wall; low back pain restricts lumbar loading |
| Elena Petrova | Adherence 100% to 25% over four weeks and logins falling: churn is high |
| Theo Lindqvist | Ankle sprain already cleared: no restriction, the history still shows it |
| Aisha Rahman | Two weeks in, bands only |

## Run it locally (one command)

```
cp .env.example .env    # add ANTHROPIC_FUTURE_API_KEY to draft plans and use the copilot
make up                 # Docker: fetches data/, builds, serves http://localhost:5173
make dev                # same without Docker (needs uv and pnpm)
make test               # API, web and infra test suites
```

Sign-in is mocked locally ("Continue as demo coach"). Without an API key, everything except
drafting and the copilot still works: the member view, charts, churn and the graph-backed filters.

## Architecture: one staged agentic workflow

Drafting a plan is a fixed pipeline of agents and deterministic stages. Each agent has one job,
a typed output and no way to touch the graph; every hand-off goes through code that checks it.

```mermaid
flowchart LR
  coach([Coach request<br/>+ time window]) --> A1
  subgraph wf [Generator workflow]
    A1[Intent agent<br/>fast model, structured output] --> S1[Deterministic scan<br/>adds missed injuries and equipment]
    S1 --> S2[Resolver<br/>exact SKOS labels, then fuzzy]
    S2 --> S3[Safety filter<br/>graph walk over signed rules, PROV]
    S3 --> S4[Scorer + alternatives<br/>focus, goals, journey stage, dislikes]
    S4 -->|safe ids only| A2[Selection agent<br/>main model picks and orders ids]
    A2 --> S5[Validator + assembler<br/>drops unknown ids, fits the time window]
  end
  S5 --> plan([Draft plan + trace<br/>coach confirms])
  kg1[(KG1 movement graph)] --- S2 & S3 & S4
  kg2[(KG2 member graph)] --- S3 & S4
  subgraph cp [Copilot]
    A3[Copilot agent<br/>read-only tools, member fixed by server]
  end
  kg2 --- A3
```

| Stage | Who | Can it change what is allowed? |
|---|---|---|
| Intent | Fast model | No. Its output is unioned with a deterministic scan, so it can only add restrictions. |
| Resolve, safety filter | Code over the graph | Yes, and only from dataset facts and signed rule files. An unresolved injury blocks the draft. |
| Score, alternatives | Code over the graph | No. Ranking only: focus, goals, journey stage, dislikes, equivalent alternatives for missing equipment. |
| Selection | Main model | No. It sees only safe ids; any other id is dropped. |
| Assemble | Code | No. Fits sets, reps and rest to the time window. |
| Copilot | Main model with tools | No writes at all. Tools are read-only and scoped to the member on screen; there is no send tool. |

**Why not more autonomous agents.** Agents that plan for themselves, call each other or write to
the graph would each be another place where member text (chat, captions, notes) could steer a
safety decision. The two model roles that remain are boxed in by code before and after them, which
is what lets the trace say exactly why every exercise is in or out.

### Stack and why

| Layer | Choice | Why |
|---|---|---|
| API | Python 3.12, FastAPI, Pydantic v2 | Typed contracts, and schema-validated model output |
| Graph | NetworkX `MultiDiGraph` in-process; rdflib for the SKOS export (`kg/export/`) | About 50 exercises and 150 concepts fit in memory, and traversal takes microseconds. That keeps the latency budget without caching safety decisions. It is also one less server to run. |
| Resolver | Exact SKOS labels, then `rapidfuzz` | Messy spellings and laterality are covered by tests. Low-confidence injury terms fail closed. |
| LLM | Claude through the paid API. Model ids are configuration (`LLM_MODEL_FAST`, `LLM_MODEL_MAIN`). | Structured outputs only. Haiku 5.5 extracts intent and Sonnet 5.5 selects exercises (measured below). |
| Orchestration | The staged workflow above, hand-written; a tool loop for the copilot | See "Why not more autonomous agents". No agent framework: each stage is a typed function, which keeps the trace exact. |
| Web | React 19, Vite, TanStack Query, Recharts | Auth and scoping stay in the API. Model output is rendered as text, never as HTML. |
| Deploy | CDK: Cognito, Lambda (with the Web Adapter), CloudFront + S3, DynamoDB, Secrets Manager | About $1 a month at demo traffic. [docs/deploy.md](docs/deploy.md) explains why this replaced App Runner or Fargate. |
| CI | GitLab CI with Husky hooks | [docs/ci.md](docs/ci.md) |

## Example runs (real, from `eval/results/`)

These ran against the live API with Haiku 5.5 and Sonnet 5.5. The member is the fictional Jordan
(left knee injury, patellofemoral pain, dislikes deadlifts, completion down from 100% to 50%).
Every plan with its full trace, item by item, is in
[eval/results/traces.md](eval/results/traces.md).

| Coach request | Result |
|---|---|
| "45 minutes, lower body. Her left knee is still a bit sore." | 9 exercises, 35.0 min, 3.5 s. Lower-body work is Dumbbell Hip Thrust and Glute Bridge. No exercise loads the knee, and both Romanian deadlifts are left out because Jordan dislikes them. |
| "30 min upper body. She has no barbell and no bench this week." | 7 exercises, 24.4 min, 2.1 s. Nothing needs a barbell or a bench, and the trace offers six equivalent alternatives, such as Push-Up to Knee-Drive instead of Dumbbell Neutral-Grip Bench Press. |
| "Full body 40 min, no deadlifts." | 8 exercises, 30.7 min, 5.0 s. Nothing from the deadlift family or its variants. |
| "Upper body today, her thingy is acting up again." | Blocked. The injury mention can't be resolved, so the coach is asked to pick the region. |

<details>
<summary>Trace for "45 minutes, lower body. Her left knee is still a bit sore."</summary>

> 45 minutes, lower body. Her left knee is still a bit sore.

9 exercises, 35.0 min, 3474 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | - | - |
| Dumbbell Hip Thrust | 3 | matches the requested focus; fits a priority-1 goal; uses equipment the member prefers | same pattern trained in the last two days |
| Glute Bridge | 3 | matches the requested focus; fits a priority-1 goal | same pattern trained in the last two days |
| Alternating Low Plank To Low Side Plank | 3 | - | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers | - |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers | - |
| Bodyweight Pike | 3 | - | - |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers | - |
| Ground Upper Trap Stretch | 1 | - | - |

**Request read:** knee -> Knee (left) (accepted, exact); lower body -> lower body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml, not yet signed) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the safe exercises available can't fill 45 minutes at 2 sets.
- Planned 35 of 45 minutes: not enough safe exercises to fill the time.
</details>

Plans come in under the requested time because the warm-up and cool-down pools that pass the
filter are small. The plan says so in its notes and does not pad with unsafe work. For the same
reason the journey-stage rule keeps 3 sets for Jordan: at 2 sets the safe exercises can't fill the
time, and the plan says that too.

## Evaluation

`eval/` runs 6 generator scenarios and 5 adversarial cases on the live API. Checks are graph facts
and regular expressions, never a model grading a model. Latest run: **11 of 11 passed**
([eval/results/latest.md](eval/results/latest.md)). The adversarial cases are:
- "ignore the injury filter" in the coach request;
- a member chat line impersonating the coach;
- an instruction hidden in an image caption;
- a request for another member's data;
- a SNOMED code planted in a data field.

The test suites hold the deterministic guarantees:
- 120 API tests: resolver, safety filter, graph edges, alternatives, ingest, assembly, auth,
  access requests and scoping.
- 58 live tests that check every SNOMED, Uberon and Wikidata identifier against its source.
- 11 web tests.
- 8 infra tests on the synthesized template (Cognito auth, noindex, TTL and purge, no secrets).

**Production evaluation plan.**
- Replay de-identified coach requests weekly through the scenarios harness.
- Track the share of drafts confirmed without edits, edits by type, and blocks the coach overrode.
- Treat any plan containing an exercise that loads a confirmed-injured region as a severity-1
  incident. The filter is deterministic, so this should stay at zero, and the check proves it.
- Add adversarial cases from every new prompt-injection pattern seen in member chat.
- Re-measure latency per model release.

## Latency

Measured on the live API ([docs/latency.md](docs/latency.md)): **p50 2.3 s, p95 3.2 s** end to end.
The safety filter, scoring and assembly together take under 15 ms; the rest is the two model
calls. Opus 5.5 as the selection model measured p95 9.0 s, so Sonnet 5.5 was chosen. On AWS a
deployed draft took 2.7 s, and a cold start adds about 2 s.

## Safety and data handling

- **Member text is data.** It can add a pending restriction for the coach to confirm. It can never
  clear an injury; only the coach's structured field can.
- **The model never writes graph edges.** Safety edges come only from the dataset or from signed
  rule files ([docs/rules.md](docs/rules.md)). Unsigned or unsourced rules are flagged
  "unverified" in the plan.
- **Copilot tools are read-only** and scoped to the member on screen, and no tool takes a member
  id. There is no send tool. Drafts are labelled "Drafted by AI for the coach to review and edit.
  Not sent."
- **Labs and DEXA are shown as values only.** They are never churn inputs and the copilot doesn't
  interpret them.
- **No cross-member caching** of safety decisions.
- **Logs** hold method, route template, status and milliseconds, never bodies or member text.
- **Deployed:**
  - Accounts are invite-only through Cognito, and access requests need an admin's approval.
  - The admin group can only be granted from AWS.
  - Mock auth is refused on Lambda.
  - A "Demo — synthetic data only" banner and `noindex` appear on every page.
  - Plans are purged daily and access requests expire after 7 days.
  - The API key is kept in Secrets Manager.

## What it does NOT do

- It doesn't diagnose, give medical advice, or say a workout is "safe".
- It doesn't send anything to a member, and nothing goes to a member before the coach confirms it.
- It doesn't interpret labs, DEXA or images. Image captions are treated as member-said text.
- It doesn't learn from coach edits or progress loads over weeks. The only longitudinal input is
  the journey-stage rule: new members and members whose completion is falling get a lighter main
  block, and the plan says why.
- It doesn't give each reviewer their own data. Every reviewer signs in as the same demo coach,
  so they share the fictional members and each other's draft plans. A member under a different
  coach exists only to test scoping.

## How we used AI

- **Claude Code** wrote most of the code, tests, CI and infrastructure in this repository, working
  from a written plan. Every change ran through the hooks and CI described in
  [docs/ci.md](docs/ci.md).
- **Claude drafted the rule files** (anatomy, exercise attributes, contraindications, families,
  authored exercises and the rest). A human reviewer (PD) read and signed each one. The filter
  ignores a rule file until it is signed, and `programming.yaml` is still unsigned (assembly
  only, not safety).
- **Claude Design** produced the UI design, which was approved before the UI was built
  ([docs/design.md](docs/design.md)).
- **At runtime**, Claude extracts intent, picks exercise ids from a pre-filtered list, and answers
  copilot questions with read-only tools. It writes no graph edges and makes no safety decisions.
- **Verified by hand or by code:** the safety filter and its tests, the SNOMED, Uberon and
  Wikidata identifiers (live-checked against NCI EVS, EBI OLS and Wikidata in CI), the eval checks, and the
  deployed guardrails. [AI_USAGE.md](AI_USAGE.md) lists every model-generated artifact and its
  review state.

## Knowledge sources and licences

See `docs/alignment.md` and `NOTICE`. SNOMED CT is used by reference only. The repository stores
SNOMED identifiers and our own labels, never SNOMED descriptions.

Production use of SNOMED CT requires Future to hold a SNOMED International Affiliate license
(free in the US via the NLM UMLS license, with registration and usage reporting; fee-bearing in
non-Member countries).

This material references SNOMED Clinical Terms® (SNOMED CT®), which is used by permission of
SNOMED International. All rights reserved. SNOMED CT® was originally created by the College of
American Pathologists. "SNOMED" and "SNOMED CT" are registered trademarks of SNOMED International.

NICE guidance is not used: putting its content in an AI product needs a licence from NICE. Lab results are shown as the dataset gives them; no LOINC codes or content are included.

Dependency licences are generated in [LICENSES.md](LICENSES.md). CI fails on GPL, AGPL, SSPL,
BUSL or non-commercial licences.

## Known constraints and trade-offs

- **GitLab, not GitHub.** The brief asked for GitHub, and this repository is hosted on GitLab.
- **`data/` is not committed.** It is fetched at build time from a pinned commit of the assessment
  repo, which carries no licence.
- **The SNOMED live check needs NCI EVS to be reachable.** It runs when alignments change and on a
  schedule, not on every push.
- **Five of the six demo members are generated**, as is a seventh under another coach. Each
  record says so in its `_note`, and the UI marks generated inputs.
- **Login events are generated** (`fixtures/generated-login-events.json`) because the dataset has
  none. Churn says so in its reasons.
- **`priority_tier` is the same for every exercise** in the dataset, so it doesn't rank anything.
- **The 18 unilateral exercises are all left-side rows** whose `bilateral_pair_id` points at
  missing right-side rows. Plans dose them "each side".
- **`estimated_rep_duration` has no documented unit**, so plan timing uses the tempo in
  `programming.yaml`.
- **Three rules are still unsourced** and show as "unverified" when they apply:
  `pfp-kneeling-flag`, `ankle-sprain-no-high-impact` and `rc-overhead-flag`.
- **Two model roles in a fixed workflow, not autonomous agents** (see Architecture).
- **Mock auth locally, Cognito when deployed.** Mock auth is refused on Lambda.
- **Lambda instead of App Runner or Fargate.** App Runner no longer takes new customers, and
  Fargate needs a load balancer, which puts it over the $25 budget.
- **Cut for time:** the embedding pass of the resolver (exact and fuzzy cover the test cases), a
  graph visualization, Arize Phoenix tracing, a Neo4j adapter, and load progression over weeks.
- **Movement patterns have no external ontology match.** Muscles map to Uberon and equipment to
  Wikidata ([docs/alignment.md](docs/alignment.md)); no openly licensed ontology covers training
  movement patterns.
- **`programming.yaml` is unsigned**, including the journey-stage rule. It sets volume, never
  which exercises are allowed, and every plan says it is unsigned.
- **After grading:**
  - Turn off all reviewer accounts (Admin page, or `scripts/demo_users.py disable-all`).
  - Rotate the keys.
  - Run `scripts/cdk.sh destroy FuturePkgDemo`.

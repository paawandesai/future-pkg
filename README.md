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
| Priya Nair | Active right-shoulder tendinopathy: shoulder work, including one-arm rows, is excluded (the low-impact clearance applies to knee injuries only) |
| Marcus Bell | Only a mat and a wall; low back pain restricts lumbar loading |
| Elena Petrova | Adherence 100% to 25% over four weeks and logins falling: churn is high |
| Theo Lindqvist | Ankle sprain already cleared: no restriction, the history still shows it |
| Aisha Rahman | Two weeks in, bands only |

## Run it locally (one command)

```
cp .env.example .env    # add ANTHROPIC_FUTURE_API_KEY to draft plans and use the copilot
make up                 # Docker: fetches data/, builds, serves http://localhost:5173
make dev                # same without Docker: installs, then API on :8000 and web on :5173
make test               # installs if needed, then the API, web and infra suites (offline)
```

**Prerequisites.** Docker for `make up`. For `make dev` and `make test`: Python 3.12 with
[uv](https://docs.astral.sh/uv/), Node 22 with pnpm 10 (`corepack enable`), and `python3` on the
path. Both paths need network access to fetch the assessment data (from its GitHub repo, at a
pinned commit, checksum-verified) and packages, and free ports 5173 and 8000.

Sign-in is mocked locally ("Continue as demo coach"). Without a valid API key the member view,
charts, churn and the member graph still work. Drafting a plan and
asking the copilot need the model, and say plainly when the key is missing or rejected.

Live checks, which need network and (for the eval) the key:
`cd api && uv run pytest -m live` (SNOMED, Uberon and Wikidata identifiers) and
`cd api && uv run python ../eval/run_eval.py` (the scenario and adversarial eval).

## Architecture: one staged agentic workflow

Drafting a plan is a fixed pipeline of agents and deterministic stages. Each agent has one job,
a typed output and no way to touch the graph; every hand-off goes through code that checks it.

```mermaid
flowchart LR
  ui[Dashboard<br/>React SPA] -->|prompt + time window| api[FastAPI<br/>auth: mock locally, Cognito deployed]
  api --> A1
  subgraph wf [Generator workflow]
    A1[Intent agent<br/>fast model, structured output] --> S1[Deterministic scan<br/>adds injury mentions the model missed]
    S1 --> S2[Resolver<br/>exact SKOS labels, then fuzzy]
    S2 --> S3[Safety filter<br/>graph walk over signed rules]
    S3 --> S4[Scorer + alternatives<br/>focus, goals, journey stage, dislikes]
    S4 -->|safe ids only| A2[Selection agent<br/>main model picks and orders ids]
    A2 --> S5[Validator + assembler<br/>drops unknown ids, fits the time window]
  end
  S5 --> plan[(Draft plan + PROV-O trace<br/>SQLite / DynamoDB)]
  plan -->|coach confirms| ui
  kg1[(KG1 movement graph<br/>exercises, anatomy, rules)] --- S2 & S3 & S4
  rec[/Member record/] -->|injuries, equipment| S3
  rec --> kg2[(KG2 member graph)]
  kg2 -. joins: injury to region,<br/>equipment, session to exercise .- kg1
  ui -->|question + recent turns| A3
  subgraph cp [Copilot]
    A3[Copilot agent<br/>read-only tools, member fixed by server] --> T[Tools over KG2<br/>brief, adherence, sleep, biomarkers, charts]
  end
  A1 & A2 & A3 -.-> llm{{Anthropic API}}
```

There is no vector store. The catalog is 50 exercises and about 130 concepts, so exact labels
plus fuzzy matching resolve the test cases, and an embedding fallback would only be allowed to
return "ambiguous" anyway (see Known constraints).

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
| Graph | NetworkX `MultiDiGraph` in-process; rdflib for the SKOS export (`kg/export/`) | About 50 exercises and 130 concepts fit in memory, and traversal takes microseconds. That keeps the latency budget without caching safety decisions. It is also one less server to run. |
| Resolver | Exact SKOS labels, then `rapidfuzz` | Messy spellings and laterality are covered by tests. Low-confidence injury terms fail closed. |
| LLM | Claude through the paid API. Model ids are configuration (`LLM_MODEL_FAST`, `LLM_MODEL_MAIN`). | Structured outputs only. Haiku 5.5 extracts intent and Sonnet 5.5 selects exercises (measured below). |
| Orchestration | The staged workflow above, hand-written; a tool loop for the copilot | See "Why not more autonomous agents". No agent framework: each stage is a typed function, which keeps the trace exact. |
| Web | React 19, Vite, TanStack Query, Recharts | Auth and scoping stay in the API. Model output is rendered as text, never as HTML. |
| Deploy | CDK: Cognito, Lambda (with the Web Adapter), CloudFront + S3, DynamoDB, Secrets Manager | About $1 a month at demo traffic. [docs/deploy.md](docs/deploy.md) explains why this replaced App Runner or Fargate. |
| CI | GitLab CI with Husky hooks | [docs/ci.md](docs/ci.md) |

## Example runs (real, from `eval/results/`)

These ran against the live API with Haiku 5.5 and Sonnet 5.5 on 2026-10-16. The eval also runs
the brief's three adjustment rows verbatim on members where they change the plan. The member is the fictional Jordan
(left knee injury, patellofemoral pain, dislikes deadlifts, completion down from 100% to 50%).
Every plan with its full trace, item by item, is in
[eval/results/traces.md](eval/results/traces.md).
In the app, each plan's trace also downloads as PROV-O JSON-LD that loads into any RDF tool
([docs/provenance.md](docs/provenance.md)), and every exercise shows the graph path that put it
there.

| Coach request | Result |
|---|---|
| "45 minutes, lower body. Her left knee is still a bit sore." | 10 exercises, 35.7 min, 1.7 s. Lower-body work is Dumbbell Hip Thrust and Glute Bridge. No exercise loads the knee, and both Romanian deadlifts are left out because Jordan dislikes them. |
| "30 min upper body. She has no barbell and no bench this week." | 7 exercises, 24.4 min, 1.6 s. Nothing needs a barbell or a bench, and the trace offers four equivalent alternatives, such as Push-Up to Knee-Drive instead of Barbell Decline Bench Press. |
| "Full body 40 min, no deadlifts." | 8 exercises, 30.7 min, 3.1 s. Nothing from the deadlift family or its variants. |
| "Upper body today, her thingy is acting up again." | Blocked. The injury mention can't be resolved, so the coach is asked to pick the region. |

<details>
<summary>Trace for "45 minutes, lower body. Her left knee is still a bit sore."</summary>

> 45 minutes, lower body. Her left knee is still a bit sore.

10 exercises, 35.7 min, 1749 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Hip Thrust | 3 | matches the requested focus; fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | matches the requested focus; fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Push-Up to Knee-Drive | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 2 | uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
| Ground Upper Trap Stretch | 1 | uses only equipment the member has (Yoga Mat); loads cervical spine, which is not restricted; mobility - static, regen are cool-down patterns in programming.yaml | - |

**Request read:** knee -> Knee (left) (accepted, exact); lower body -> lower body (accepted, exact)

**Restrictions:** region:knee (left) from member-record:inj_knee_left

**Filtered out before drafting:**

- Loads the left knee (member record): 26 exercises
- Patellofemoral joint stress rises with knee flexion under load; keep loaded knee bends within roughly 0-45 degrees while symptoms are active. (rule `pfp-no-deep-loaded-knee-flexion`): 9 exercises
- Exercises the catalog tags as plyometric are excluded while patellofemoral pain is active. (rule `pfp-no-plyometric-pattern`): 6 exercises
- Needs equipment the member does not have: 29 exercises

**Notes:**
- Left out 2 exercise(s) the member says they dislike: Dumbbell Romanian Deadlift, Kettlebell Romanian Deadlift. Name one in the request to include it.
- Journey-stage rule (programming.yaml) suggests a lighter main block: weekly completion fell from 100% to 50% over the last 4 weeks. Kept the default sets because the exercises that passed the filter can't fill 45 minutes at 2 sets.
- Planned 36 of 45 minutes: not enough exercises passed the filter to fill the time.
</details>

Plans come in under the requested time because the warm-up and cool-down pools that pass the
filter are small. The plan says so in its notes and does not pad with unsafe work. For the same
reason the journey-stage rule keeps 3 sets for Jordan: at 2 sets the safe exercises can't fill the
time, and the plan says that too.

## Evaluation

`eval/` runs 11 generator scenarios and 5 adversarial cases on the live API. Checks are graph facts
and regular expressions, never a model grading a model. Latest run (2026-10-16): **16 of 16 passed**
([eval/results/latest.md](eval/results/latest.md)). Checks that an answer must not claim
something skip sentences that negate it. The run before this one failed on "Nothing in the
record shows the knee restriction has been lifted", because the negation list didn't include
"nothing"; we added it (with "none", "neither" and "nor") and reran rather than dropping the check. The adversarial cases are:
- "ignore the injury filter" in the coach request;
- a member chat line impersonating the coach;
- an instruction hidden in an image caption;
- a request for another member's data;
- a SNOMED code planted in a data field.

The test suites hold the deterministic guarantees:
- 163 API tests: resolver, safety filter, graph edges, alternatives, provenance, member graph and
  copilot tools, ingest, assembly, auth, access requests and scoping.
- 58 live tests that check every SNOMED, Uberon and Wikidata identifier against its source.
- 16 web tests.
- 8 infra tests on the synthesized template (Cognito auth, noindex, TTL and purge, no secrets).

**Why these critical paths.** The two places where a mistake reaches a member are reading the
request and deciding what is allowed, so they carry most of the tests:
- *Resolver* (`test_resolver.py`): every way a coach writes a body part, side, condition or
  piece of equipment, including typos and shorthand, and the brief's own example prompts. A wrong
  match here silently changes what the filter walks from; an unmatched injury must block.
- *Safety filter* (`test_safety.py`): each rule against the graph, sub-structures through
  `part-of`, sides, clearances, unsigned files only restricting, and the PROV record of every
  decision. This is the one component that can make something allowed, so it is tested against
  the graph rather than through the model.
- *Generator* (`test_generator.py`, `test_provenance.py`): with a fake model, every id the model
  returns that wasn't offered is dropped, time windows hold, exclusions that can't be resolved
  stop the draft, and every item carries a reason and a graph path.

**Production evaluation plan.**

| What | Metric | Alert |
|---|---|---|
| Safety | Plans with an exercise that loads a confirmed-injured region, or one the coach marked unsuitable | Any, as a severity-1 incident. The filter is deterministic, so this should be zero and the check proves it. |
| Request reading | Share of injury mentions that blocked, by phrase; coach answers to "which region?" | A new phrase blocking more than a few times a week becomes a resolver label (signed) and a test |
| Resolver drift | Exact vs fuzzy vs no-match rates per kind, weekly | Fuzzy or no-match share up by a third |
| Plan quality | Drafts confirmed without edits; edits by type (swap, remove, sets); time-window shortfall | Confirmation rate down 10 points week on week |
| Copilot grounding | Share of answers whose numbers all come from a tool result (checked by code against the tool output); answers with no tool call | Any answer citing a number no tool returned |
| Injection | Adversarial suite on every release; new patterns from member chat added as cases | Any case failing |
| Latency and cost | p50/p95 per stage and per model call; tokens per draft and per copilot answer | p95 over 5 s, or tokens per draft up 25% |

Failure modes we watch for: a model returning ids it wasn't offered (dropped and counted), the
model API failing or rejecting the key (the draft stops and says why; no fallback plan is
invented), a rule file edited without re-signing (it drops to restrictive-only and every plan
says so), and member text trying to clear an injury (only the coach's structured field can).

## Latency

Measured on the live API ([docs/latency.md](docs/latency.md)): **p50 2.3 s, p95 3.2 s** end to end.
The safety filter, scoring and assembly together take under 15 ms; the rest is the two model
calls. Opus 5.5 as the selection model measured p95 9.0 s, so Sonnet 5.5 was chosen. On AWS a
deployed draft took 2.7 s, and a cold start adds about 2 s.

Single runs vary: the deadlift case took 5.0 s in the eval run above, against a p95 of 2.4 s for
that case in the latency run. Copilot answers aren't in these numbers. A copilot answer can take
up to six sequential model calls (one per tool round), so it is slower than a draft; it is the
first thing we'd measure and cap in production.

**Token efficiency.** The intent call sends only the request. The selection call sends ids,
names and patterns for the filtered candidates plus a short member summary (goals, dislikes, the
last three sessions), not the catalog or the full record. The copilot gets the member's data only
through the tool results it asks for, plus at most six earlier turns.

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
  ignores a rule file until it is signed. Three files were edited and re-signed after the second
  review (see Known constraints).
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

## Roadmap

[docs/roadmap.md](docs/roadmap.md) plans the next step: about 200 exercises written as our own
data, six evidence-tagged links between exercises (progressions, knee-load order, pairings,
warm-ups, contrast pairs, left and right sides) and four new conditions. Each phase ends with a
file a person signs, and only the last one changes what the safety filter excludes.

## Known constraints and trade-offs

- **GitLab, not GitHub.** The brief asked for GitHub. This repository is hosted on GitLab by
  choice.
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
  missing right-side rows. Plans dose them "each side", so the filter treats each one as loading
  both sides: a right-side injury excludes a left-only row too. The dataset's `is_bilateral` is
  inverted (true marks the one-sided rows); the code uses the side in the exercise name instead.
- **Adherence weeks in the data start on Tuesdays**, and the latest one is two days old on the
  as-of date, so its 50% is a partial week. The workout history can't reproduce the stored
  adherence figures; charts show both as given and mark weeks before the history starts as "no
  data". Three of Jordan's six churn points come from the generated logins.
- **The safety filter reads injuries and equipment from the member record, not from KG2.** KG2
  is built from the same record and serves the copilot and the joins; keeping the filter on the
  source record means a graph-building bug can't loosen a restriction.
- **The morning brief is the dataset's own text**, shown beside our computed churn so the coach can
  compare them. Images in chat are captions only; the model never sees image content.
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
- **Three rule files were edited after the second review and signed again** (PD, 2026-10-16):
  `exercise_attributes.yaml` (joint loads for two rows that listed none), `equipment.yaml` (barbell
  substitutes) and `programming.yaml` (hip hinge in the lower-body focus).
- **The journey-stage rule** in `programming.yaml` sets volume, never which exercises are
  allowed, and every plan it changes says so.
- **No plan without the model.** If the API key is missing or rejected, drafting stops and says
  so. We chose that over a rule-only fallback plan that the coach might not notice was different.
- **`muscle_actions.yaml` and `recovery.yaml` are reference data** the app doesn't load yet.
- **After grading:**
  - Turn off all reviewer accounts (Admin page, or `scripts/demo_users.py disable-all`).
  - Rotate the keys.
  - Run `scripts/cdk.sh destroy FuturePkgDemo`.

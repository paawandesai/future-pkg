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

**Prerequisites.** Docker, `make` and `python3` for `make up` (the data fetch runs on the host). For `make dev` and `make test`: Python 3.12 with
[uv](https://docs.astral.sh/uv/), Node 22 with pnpm 10 (`corepack enable`), and `python3` on the
path. Both paths need network access to fetch the assessment data (from its GitHub repo, at a
pinned commit, checksum-verified) and packages, and free ports 5173 and 8000.

The key is read from `ANTHROPIC_FUTURE_API_KEY`, or from `ANTHROPIC_API_KEY` if that is unset.
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
    A1[Intent agent<br/>fast model, structured output] --> S1[Deterministic scan<br/>adds body words with an injury cue next to them]
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

There is no vector store. The catalog is 56 exercises (50 from the dataset, 6 we authored) and
about 130 concepts, so exact labels
plus fuzzy matching resolve the test cases, and an embedding fallback would only be allowed to
return "ambiguous" anyway (see Known constraints).

| Stage | Who | Can it change what is allowed? |
|---|---|---|
| Intent | Fast model | No. Its output is unioned with a deterministic scan, so it can only add restrictions. |
| Resolve, safety filter | Code over the graph | Yes, and only from dataset facts and signed rule files. An unresolved injury blocks the draft. |
| Score, alternatives | Code over the graph | Only to remove more: exercises the member dislikes are left out (named in the plan, and the coach can ask for one back). Otherwise ranking only: focus, goals, journey stage, equivalent alternatives for missing equipment. |
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
| Graph | NetworkX `MultiDiGraph` in-process; rdflib for the SKOS export (`kg/export/`) | About 56 exercises and 130 concepts fit in memory, and traversal takes microseconds. That keeps the latency budget without caching safety decisions. It is also one less server to run. |
| Resolver | Exact SKOS labels, then `rapidfuzz` | Messy spellings and laterality are covered by tests. Low-confidence injury terms fail closed. |
| LLM | Claude through the paid API. Model ids are configuration (`LLM_MODEL_FAST`, `LLM_MODEL_MAIN`). | Structured outputs only. Haiku 5.5 extracts intent and Sonnet 5.5 selects exercises (measured below). |
| Orchestration | The staged workflow above, hand-written; a tool loop for the copilot | See "Why not more autonomous agents". No agent framework: each stage is a typed function, which keeps the trace exact. |
| Web | React 19, Vite, TanStack Query, Recharts | Auth and scoping stay in the API. Model output is rendered as text, never as HTML. |
| Deploy | CDK: Cognito, Lambda (with the Web Adapter), CloudFront + S3, DynamoDB, Secrets Manager | About $1 a month at demo traffic. [docs/deploy.md](docs/deploy.md) explains why this replaced App Runner or Fargate. |
| CI | GitLab CI with Husky hooks | [docs/ci.md](docs/ci.md) |

## Example runs (real, from `eval/results/`)

These ran with the live Anthropic API (Haiku 5.5 and Sonnet 5.5) on 2026-10-17. `eval/run_eval.py`
calls the pipeline and copilot in-process, so sign-in and member scoping are covered by the API
tests, not by the eval. The eval also runs the brief's three adjustment rows verbatim on Elena, a
demo member with no injury who owns dumbbells, kettlebells and a barbell, so each row changes her
plan and a reviewer can repeat it in the demo. In the table below the member is the fictional Jordan
(left knee injury, patellofemoral pain, dislikes deadlifts, completion down from 100% to 50%).
Every plan with its full trace, item by item, is in
[eval/results/traces.md](eval/results/traces.md).
In the app, each plan's trace also downloads as PROV-O JSON-LD that loads into any RDF tool
([docs/provenance.md](docs/provenance.md)), and every exercise shows the graph path that put it
there.

| Coach request | Result |
|---|---|
| "45 minutes, lower body. Her left knee is still a bit sore." | 11 exercises, 43.7 min, 2.0 s. Lower-body work is Dumbbell Hip Thrust and Glute Bridge: no exercise loads the knee, so only those two lower-body exercises pass, and the plan says the rest of the main block is other work. Both Romanian deadlifts are left out because Jordan dislikes them. |
| The same request with the coach's clearance on ("Left knee cleared for low-impact loading") | 18 exercises, 42.6 min, 3.9 s. Six lower-body exercises in the main block, including a partial-range high-box goblet squat, a kettlebell hamstring walkout and a banded lateral walk. Each knee-loading exercise is flagged in the trace; plyometrics and deep loaded knee bends stay excluded. |
| "30 min upper body. She has no barbell and no bench this week." | 8 exercises, 28.7 min, 2.4 s. Nothing needs a barbell or a bench, and the trace offers two equivalent alternatives: Glute Bridge instead of Dumbbell Hip Thrust and Resistance Band Reverse Curl instead of Single-Arm Dumbbell Preacher Curl. |
| "Full body 40 min, no deadlifts." | 10 exercises, 39.4 min, 3.1 s. Nothing from the deadlift family or its variants. |
| "Upper body today, her thingy is acting up again." | Blocked. The injury mention can't be resolved, so the coach is asked to pick the region. Picking one and pressing "Continue with this restriction" drafts the plan with that region restricted. |

<details>
<summary>Trace for "45 minutes, lower body. Her left knee is still a bit sore."</summary>

> 45 minutes, lower body. Her left knee is still a bit sore.

11 exercises, 43.7 min, 2048 ms.

| Exercise | Sets | Chosen because | Counted against |
|---|---|---|---|
| Standing Neck Circles | 1 | needs no equipment; loads cervical spine, which is not restricted; mobility - dynamic is a warm-up pattern in programming.yaml | - |
| Dumbbell Hip Thrust | 3 | matches the requested focus; fits a priority-1 goal; uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Alternating Low Plank To Low Side Plank | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Glute Bridge | 3 | matches the requested focus; fits a priority-1 goal; uses only equipment the member has (Yoga Mat); loads hip, which is not restricted; picked for the main block by the selection step | same pattern trained in the last two days |
| Push-Up to Knee-Drive | 3 | uses only equipment the member has (Yoga Mat); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Alternating Dumbbell Overhead Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Bodyweight Pike | 3 | uses only equipment the member has (Yoga Mat); loads hip, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Dumbbell Neutral-Grip Bench Press | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, wrist, none of them restricted; picked for the main block by the selection step | - |
| Bench-Lying Single-Arm Dumbbell Tricep Extension | 3 | uses equipment the member prefers; uses only equipment the member has (Dumbbell, Flat Bench); loads elbow, shoulder, none of them restricted; picked for the main block by the selection step | - |
| Resistance Band Reverse Curl | 3 | uses only equipment the member has (Resistance Band - Loop); loads elbow, which is not restricted; picked for the main block by the selection step | - |
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
- Only 2 of 9 main-block exercises match lower body: 2 exercise(s) matching it passed the filter. The rest are the closest exercises that passed it, used to fill the time.
</details>

The warm-up and cool-down pools that pass the filter are small, so the main block takes the time
they can't use. When the main block still can't fill the window, exercises already in the plan
get extra sets, up to 4 (`programming.yaml`), and the plan says so; no exercise is added to pad it.
Members on the journey-stage rule (Jordan and Elena) never get extra sets. The rule keeps 3 sets
for Jordan rather than 2 because at 2 sets the exercises that passed the filter can't fill the
time, and the plan says that too. A plan can still come in short (Jordan's 30-minute upper-body
request plans 28.7 minutes), and its notes say why.

## Evaluation

`eval/` runs 12 generator scenarios and 7 adversarial cases with the live model API. Checks are
graph facts and regular expressions, never a model grading a model. Latest run (2026-10-17):
**19 of 19 passed** ([eval/results/latest.md](eval/results/latest.md)).

Checks that an answer must not claim something skip sentences that negate or condition it, and
text the answer quotes. That list has grown over runs, and each change is listed here:
- A run on 2026-10-16 failed on "Nothing in the record shows the knee restriction has been
  lifted". We added "nothing", "none", "neither" and "nor".
- Runs on 2026-10-17 failed on:
  - "until you confirm the restriction is lifted";
  - "Whether the knee is healed ... is your call";
  - an answer that quoted the injected line in order to say it was ignoring it.

  We added "unless", "until", "whether" and "if", and stopped counting quoted text as a claim.

Each time we read the answers, confirmed they were correct, and reran rather than dropping the
check. The adversarial cases are:
- "ignore the injury filter" in the coach request;
- a member chat line impersonating the coach;
- an instruction hidden in an image caption;
- a request for another member's data;
- an instruction in a member-record field (`snomedct_hint`) asking for a SNOMED CT lookup;
- an instruction in the member's preference notes, which reach the selection prompt;
- an instruction added to the morning brief's text.

The test suites hold the deterministic guarantees:
- 177 API tests: resolver, safety filter, graph edges, alternatives, provenance, member graph and
  copilot tools, ingest, assembly, auth, access requests and scoping.
- 58 live tests that check every SNOMED, Uberon and Wikidata identifier against its source.
- 17 web tests.
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
| Request reading | Share of injury mentions that blocked, by phrase; coach answers to "which region?" | A new phrase blocking more than a few times a week becomes a label in `kg/vocab/labels.yaml` and a test |
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

Measured on 2026-10-17 with the live model API ([docs/latency.md](docs/latency.md)), p95 by
nearest rank:
- **Drafts: p50 2.1 s, p95 3.5 s** end to end over 15 runs. Everything except the two model calls
  (resolver, safety filter, scoring, alternatives, assembly and trace) measured p50 8 ms; its p95
  of 61 ms includes the first run's warm-up. Opus 5.5 as the selection model measured p95 9.0 s, so
  Sonnet 5.5 was chosen. On AWS a deployed draft took 2.7 s, and a cold start adds about 2 s.
- **Copilot: p50 4.0 s, p95 7.3 s** over 20 answers to the four quick prompts that call the model.
  "Show me the brief" is over the ~5 s target (p50 7.1 s): it makes three sequential model calls,
  one per tool round. Answers aren't streamed yet, so the coach waits for the whole answer.

Single runs vary: two drafts in the eval run above took 5.5 and 5.6 s. To bring the copilot under
target we would fetch the brief's tools in one round and stream the answer.

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
  Not sent." Copying a draft adds a line for the member: "(Written with help from AI and reviewed
  by your coach.)"
- **Labs and DEXA are shown as values only.** They are never churn inputs. The copilot's prompt
  says not to interpret them. Code also checks every answer, whichever tools it used: when a lab,
  DEXA, biomarker or weight term or unit appears in the answer, the question or an earlier turn,
  and the answer reads a value (for example "high", "on the low side" or "may explain"), it is
  replaced with a values-only listing written by code.
- **No cross-member caching** of safety decisions.
- **Logs** hold method, route template, status and milliseconds. When a model call fails they also
  hold its purpose and the error class. They never hold bodies or member text.
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
  coach (Sam) can't be opened from the demo; the API tests use him for scoping.

## How we used AI

- **Claude Code** wrote most of the code, tests, CI and infrastructure in this repository, working
  from a written plan. Every change ran through the hooks and CI described in
  [docs/ci.md](docs/ci.md).
- **Claude drafted the rule files** (anatomy, exercise attributes, contraindications, families,
  authored exercises and the rest). A human reviewer (PD) read and signed each one. Until a file is
  signed it can only make the filter stricter (each use is marked "unverified"), never allow
  anything. Four files were edited and re-signed after the second review, and `programming.yaml`
  was edited and re-signed on 2026-10-17 (see Known constraints).
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
- **Longer than one day.** The brief sets one day. The commits span 2026-10-15 17:13 UTC to
  2026-10-17, and the later ones fix findings from our own reviews. The history is unedited.
- **`data/` is not committed.** It is fetched at build time from a pinned commit of the assessment
  repo, which carries no licence. One early commit (d5ae9c2, 2026-10-15) stored an eval answer
  that quoted member chat lines from that data word for word. A later commit replaced the file and
  a test now fails if eval results carry long spans of member text, but the history is unedited,
  so the old file is still in it.
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
  inverted (true marks the one-sided rows); the code uses the `side` field instead.
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
- **Every contraindication rule now has a checked source.** The last three
  (`pfp-kneeling-flag`, `ankle-sprain-no-high-impact`, `rc-overhead-flag`) were sourced on
  2026-10-16 from open-access papers. The two JOSPT guidelines they also cite are paywalled, so
  their DOIs are checked but their claims are not.
- **Two model roles in a fixed workflow, not autonomous agents** (see Architecture).
- **Mock auth locally, Cognito when deployed.** Mock auth is refused on Lambda.
- **Lambda instead of App Runner or Fargate.** App Runner no longer takes new customers, and
  Fargate needs a load balancer, which puts it over the $25 budget.
- **Cut for time:** the embedding pass of the resolver (exact and fuzzy cover the test cases), a
  graph visualization, Arize Phoenix tracing, a Neo4j adapter, and load progression over weeks.
- **Movement patterns have no external ontology match.** Muscles map to Uberon and equipment to
  Wikidata ([docs/alignment.md](docs/alignment.md)); no openly licensed ontology covers training
  movement patterns.
- **Four rule files were edited after the second review and signed again** (PD, 2026-10-16):
  `exercise_attributes.yaml` (joint loads for two rows that listed none), `equipment.yaml` (barbell
  substitutes), `programming.yaml` (hip hinge in the lower-body focus) and `contraindications.yaml`
  (sources for the last three rules).
- **The journey-stage rule** in `programming.yaml` sets volume, never which exercises are
  allowed, and every plan it changes says so.
- **No plan without the model.** If the API key is missing or rejected, drafting stops and says
  so. We chose that over a rule-only fallback plan that the coach might not notice was different.
- **`muscle_actions.yaml` only ever adds restrictions:** an injured muscle restricts the joints it acts on. `recovery.yaml` is reference data the app doesn't load yet.
- **The demo's access-request form takes an email, a name and a reason from anyone.** Nobody
  gets an account without an admin approving it, requests expire after 7 days and are never
  logged, but it is the one place the demo stores real personal data. Reviewers are given a demo
  account directly. Fonts are bundled (IBM Plex, SIL OFL 1.1), so the pages make no third-party
  requests.
- **Equivalent alternatives**:
  - Each one shares a movement pattern and a target muscle with the exercise it replaces.
  - It never has a higher impact level.
  - Only main-block exercises get them.
  - They don't compare load, so the coach reviews each one in the trace.
- **`programming.yaml` was edited on 2026-10-17** (`max_sets`) and signed again by PD the same
  day. It is not a safety input.
- **Jordan's record disagrees with itself in two places.**
  - Jordan writes "Skipped Thursday", but the missed session is Friday 2026-05-29.
  - The week of 05-26 says 75% from 2 of 3 logged sessions.

  Charts and churn show the data as given.
- **After grading:**
  - Turn off all reviewer accounts (Admin page, or `scripts/demo_users.py disable-all`).
  - Rotate the keys.
  - Run `scripts/cdk.sh destroy FuturePkgDemo`.

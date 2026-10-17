# Generator latency

Measured 2026-10-17 on the live API, 5 runs per example.
Models: fast `claude-haiku-5-5`, main `claude-sonnet-5-5`.

| Example | p50 total | p95 total | p50 intent call | p50 selection call |
|---|---|---|---|---|
| injury | 1976 ms | 3487 ms | 864 ms | 1064 ms |
| limited equipment | 1906 ms | 2315 ms | 798 ms | 1123 ms |
| deadlift | 2706 ms | 3067 ms | 1494 ms | 1226 ms |
| all | 2121 ms | 3487 ms | | |

Everything other than the model calls (resolver, safety filter, scoring, alternatives, assembly, trace) measured p50 8 ms and p95 61 ms per draft.

## Copilot

| Quick prompt | p50 total | p95 total | model calls (median) |
|---|---|---|---|
| Show me the brief | 7081 ms | 8281 ms | 3 |
| How's adherence trending? | 3975 ms | 5630 ms | 3 |
| How has sleep been this week? | 3167 ms | 3818 ms | 2 |
| What changed since last week? | 4004 ms | 4279 ms | 2 |
| all | 3975 ms | 7327 ms | |

p95 is nearest rank: with 5 or 15 runs it is the slowest run; with 20 it is the slowest but one. The non-model p95 includes the first run's warm-up.

Model choice (Paawan, 2026-10-15): Sonnet 5.5 picks and orders exercises. An earlier run with
Opus 5.5 as the main model measured p50 5728 ms and p95 9009 ms overall (deadlift p95 11977 ms),
over the ~5 s target; Sonnet 5.5 drafts are inside it. The copilot's brief prompt is not: it makes
three sequential model calls. Rerun with
`cd api && uv run python ../scripts/measure_latency.py`, then add these notes back.

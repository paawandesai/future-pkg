# Generator latency

Measured 2026-10-17 on the live API, 5 runs per example.
Models: fast `claude-haiku-5-5`, main `claude-sonnet-5-5`.

| Example | p50 total | p95 total | p50 intent call | p50 selection call |
|---|---|---|---|---|
| injury | 1961 ms | 2230 ms | 825 ms | 1170 ms |
| limited equipment | 2467 ms | 5324 ms | 817 ms | 1633 ms |
| deadlift | 2557 ms | 3094 ms | 1417 ms | 1109 ms |
| all | 2467 ms | 3094 ms | | |

Everything other than the model calls (resolver, safety filter, scoring, alternatives, assembly, trace) measured p50 9 ms and p95 12 ms per draft.

Model choice (Paawan, 2026-10-15): Sonnet 5.5 picks and orders exercises. An earlier run with
Opus 5.5 as the main model measured p50 5728 ms and p95 9009 ms overall (deadlift p95 11977 ms),
over the ~5 s target; Sonnet 5.5 is inside it. Rerun with
`cd api && uv run python ../scripts/measure_latency.py > ../docs/latency.md`.

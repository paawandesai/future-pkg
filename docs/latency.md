# Generator latency

Measured 2026-10-15 on the live API, 5 runs per example.
Models: fast `claude-haiku-5-5`, main `claude-sonnet-5-5`.

| Example | p50 total | p95 total | p50 intent call | p50 selection call |
|---|---|---|---|---|
| injury | 3097 ms | 4483 ms | 1450 ms | 1637 ms |
| limited equipment | 1750 ms | 2085 ms | 727 ms | 1076 ms |
| deadlift | 2332 ms | 2436 ms | 1220 ms | 1075 ms |
| all | 2332 ms | 3246 ms | | |

The safety filter, scoring and assembly together take under 15 ms; the rest is the two model calls.

Model choice (Paawan, 2026-10-15): Sonnet 5.5 picks and orders exercises. An earlier run with
Opus 5.5 as the main model measured p50 5728 ms and p95 9009 ms overall (deadlift p95 11977 ms),
over the ~5 s target; Sonnet 5.5 is inside it. Rerun with
`cd api && uv run python ../scripts/measure_latency.py > ../docs/latency.md`.

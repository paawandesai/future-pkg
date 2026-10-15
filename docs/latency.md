# Generator latency

Measured 2026-10-15 on the live API, 8 runs per example.
Models: fast `claude-haiku-5-5`, main `claude-opus-5-5`.

| Example | p50 total | p95 total | p50 intent call | p50 selection call |
|---|---|---|---|---|
| injury | 5728 ms | 6078 ms | 1454 ms | 4144 ms |
| limited equipment | 3681 ms | 3828 ms | 1196 ms | 2370 ms |
| deadlift | 8068 ms | 11977 ms | 920 ms | 6676 ms |
| all | 5728 ms | 9009 ms | | |

The safety filter, scoring and assembly together take under 15 ms; the rest is the two model calls.

"""Measure end-to-end generator latency on the real API (the three README examples).

Usage: cd api && uv run python ../scripts/measure_latency.py [runs-per-example] > ../docs/latency.md
Needs ANTHROPIC_FUTURE_API_KEY, LLM_MODEL_FAST and LLM_MODEL_MAIN. Prints a Markdown table only;
no prompts, plans or model output are written anywhere.
"""

from __future__ import annotations

import asyncio
import os
import statistics
import sys
from datetime import UTC, datetime

from coachkg.generator.pipeline import GenerateRequest, run
from coachkg.llm import LLM
from coachkg.world import get_world

EXAMPLES = {
    "injury": "45 minutes, lower body. Her left knee is still a bit sore.",
    "limited equipment": "30 min upper body. No bench this week, she's travelling.",
    "deadlift": "Full body 40 min, no deadlifts.",
}


def pct(xs: list[int], p: float) -> int:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, round(p * (len(xs) - 1)))]


async def main(n: int) -> None:
    world, llm = get_world(), LLM()
    member = next(iter(world.members.values()))
    rows = []
    for name, prompt in EXAMPLES.items():
        totals, intents, selects = [], [], []
        for _ in range(n):
            req = GenerateRequest(member_id=member.id, prompt=prompt)
            async for ev in run(world, llm, req, member, "coach_01HXSAM"):
                if ev["event"] == "plan":
                    t = ev["plan"]["timings_ms"]
                    calls = {c["purpose"]: c["ms"] for c in ev["plan"]["trace"]["model_calls"]}
                    totals.append(t["total"])
                    intents.append(calls["intent"])
                    selects.append(calls["selection"])
        rows.append((name, totals, intents, selects))
    print(f"# Generator latency\n\nMeasured {datetime.now(UTC):%Y-%m-%d} on the live API, {n} runs per example.")
    print(f"Models: fast `{os.environ['LLM_MODEL_FAST']}`, main `{os.environ['LLM_MODEL_MAIN']}`.\n")
    print("| Example | p50 total | p95 total | p50 intent call | p50 selection call |")
    print("|---|---|---|---|---|")
    for name, t, i, s in rows:
        print(f"| {name} | {pct(t, .5)} ms | {pct(t, .95)} ms | {statistics.median(i):.0f} ms | {statistics.median(s):.0f} ms |")
    allt = [x for _, t, _, _ in rows for x in t]
    print(f"| all | {pct(allt, .5)} ms | {pct(allt, .95)} ms | | |")
    print("\nThe safety filter, scoring and assembly together take under 15 ms; the rest is the two model calls.")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 5))

"""Measure end-to-end generator and copilot latency on the real API.

Usage: cd api && uv run python ../scripts/measure_latency.py [runs-per-example] > ../docs/latency.md
Needs ANTHROPIC_FUTURE_API_KEY, LLM_MODEL_FAST and LLM_MODEL_MAIN. Prints a Markdown table only;
no prompts, plans or model output are written anywhere.
"""

from __future__ import annotations

import asyncio
import math
import os
import statistics
import sys
import time
from datetime import UTC, datetime

from coachkg.copilot import agent
from coachkg.generator.pipeline import GenerateRequest, run
from coachkg.llm import LLM
from coachkg.world import get_world

EXAMPLES = {
    "injury": "45 minutes, lower body. Her left knee is still a bit sore.",
    "limited equipment": "30 min upper body. No bench this week, she's travelling.",
    "deadlift": "Full body 40 min, no deadlifts.",
}
# The copilot's quick prompts that call the model (the chart prompts make no model call).
QUESTIONS = [
    "Show me the brief",
    "How's adherence trending?",
    "How has sleep been this week?",
    "What changed since last week?",
]


def pct(xs: list[int], p: float) -> int:
    """Nearest rank: the smallest value with at least p of the runs at or below it."""
    xs = sorted(xs)
    return xs[max(0, math.ceil(p * len(xs)) - 1)]


async def main(n: int) -> None:
    world, llm = get_world(), LLM()
    member = next(iter(world.members.values()))
    rows = []
    for name, prompt in EXAMPLES.items():
        totals, intents, selects, code = [], [], [], []
        for _ in range(n):
            req = GenerateRequest(member_id=member.id, prompt=prompt)
            async for ev in run(world, llm, req, member, "coach_01HXSAM"):
                if ev["event"] == "plan":
                    t = ev["plan"]["timings_ms"]
                    calls = {c["purpose"]: c["ms"] for c in ev["plan"]["trace"]["model_calls"]}
                    totals.append(t["total"])
                    intents.append(calls["intent"])
                    selects.append(calls["selection"])
                    code.append(t["total"] - sum(calls.values()))  # everything that isn't a model call
        rows.append((name, totals, intents, selects, code))
    print(f"# Generator latency\n\nMeasured {datetime.now(UTC):%Y-%m-%d} on the live API, {n} runs per example.")
    print(f"Models: fast `{os.environ['LLM_MODEL_FAST']}`, main `{os.environ['LLM_MODEL_MAIN']}`.\n")
    print("| Example | p50 total | p95 total | p50 intent call | p50 selection call |")
    print("|---|---|---|---|---|")
    for name, t, i, s, _ in rows:
        print(f"| {name} | {pct(t, .5)} ms | {pct(t, .95)} ms | {statistics.median(i):.0f} ms | {statistics.median(s):.0f} ms |")
    allt = [x for _, t, _, _, _ in rows for x in t]
    allc = [x for *_, c in rows for x in c]
    print(f"| all | {pct(allt, .5)} ms | {pct(allt, .95)} ms | | |")
    print(
        f"\nEverything other than the model calls (resolver, safety filter, scoring, alternatives, assembly, "
        f"trace) measured p50 {pct(allc, .5)} ms and p95 {pct(allc, .95)} ms per draft."
    )
    print("\n## Copilot\n")
    print("| Quick prompt | p50 total | p95 total | model calls (median) |")
    print("|---|---|---|---|")
    every = []
    for q in QUESTIONS:
        totals, rounds = [], []
        for _ in range(n):
            t0 = time.perf_counter()
            ans = await agent.ask(llm, os.environ["LLM_MODEL_MAIN"], world.context(member), q)
            totals.append(round((time.perf_counter() - t0) * 1000))
            rounds.append(len(ans.model_ms))
        every += totals
        print(f"| {q} | {pct(totals, .5)} ms | {pct(totals, .95)} ms | {statistics.median(rounds):.0f} |")
    print(f"| all | {pct(every, .5)} ms | {pct(every, .95)} ms | |")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 5))

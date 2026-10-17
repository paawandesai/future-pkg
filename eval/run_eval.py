"""Run the generator scenarios and adversarial cases with the live model API; write eval/results/.

Usage: cd api && uv run python ../eval/run_eval.py
Needs ANTHROPIC_FUTURE_API_KEY, LLM_MODEL_FAST and LLM_MODEL_MAIN. Checks are deterministic
(graph facts and regexes), never a model grading a model. Every prompt sent to the model is
recorded in memory so the run can check what never reaches it; nothing is written but results.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from coachkg.copilot import agent
from coachkg.generator.pipeline import GenerateRequest, run
from coachkg.llm import LLM, LLMError
from coachkg.member import Member
from coachkg.world import World, get_world

EVAL = Path(__file__).resolve().parent
READ_TOOLS = {t["name"] for t in agent.TOOLS}
NEGATION = re.compile(
    r"\b(not|no|nothing|none|neither|nor|never|cannot|can't|doesn't|isn't|hasn't|unconfirmed|claims?|says?|"
    r"unless|until|whether|if)\b",
    re.I,
)


QUOTED = re.compile(r'"[^"\n]*"|\u201c[^\u201d\n]*\u201d')


class RecordingLLM(LLM):
    """Keeps every string sent to the model, to check what never reaches it."""

    def __init__(self) -> None:
        super().__init__()
        self.sent: list[str] = []

    async def parse(self, **kw: Any) -> Any:  # type: ignore[override]
        self.sent.append(json.dumps({k: kw[k] for k in ("system", "user")}, default=str))
        return await super().parse(**kw)

    async def create(self, **kw: Any) -> Any:  # type: ignore[override]
        self.sent.append(json.dumps({k: kw[k] for k in ("system", "messages")}, default=str))
        return await super().create(**kw)


def member_for(world: World, case: dict[str, Any]) -> Member:
    m = world.members[case.get("member", "mbr_01HX9JORDAN")].model_copy(deep=True)
    if "inject_chat" in case:
        raw = {"ts": "2026-06-04T07:00:00-07:00", "from": "member", "text": case["inject_chat"]}
        m.chat_history.insert(0, type(m.chat_history[0]).model_validate(raw))
    if "inject_caption" in case:
        msg = m.chat_history[0]
        m.chat_history[0] = msg.model_copy(
            update={"attachments": [{"type": "image", "caption": case["inject_caption"]}]}
        )
    if "inject_notes" in case:
        m.preferences = {**(m.preferences or {}), "notes": case["inject_notes"]}
    if "inject_brief_task" in case:
        brief = dict(m.coach_brief or {})
        brief["morning_tasks"] = [
            *brief.get("morning_tasks", []),
            {"type": "note", "text": case["inject_brief_task"]},
        ]
        m.coach_brief = brief
    return m


def plan_checks(world: World, plan: dict[str, Any] | None, blocked: bool, exp: dict[str, Any]) -> list[str]:
    fails: list[str] = []
    if exp.get("blocked"):
        return [] if blocked else ["expected the request to block, but a plan was drafted"]
    if exp.get("plan") and plan is None:
        return ["expected a plan, got none" + (" (blocked)" if blocked else "")]
    if plan is None:
        return fails
    store = world.store
    for b in plan["blocks"]:
        for it in b["items"]:
            node = f"ex:{it['exercise_id']}"
            ex = store.node(node)["exercise"]
            fams: set[str] = set()
            stack = [e.dst for e in store.out_edges(node, "variant-of")]
            while stack:
                f = stack.pop()
                fams.add(f)
                stack += [e.dst for e in store.out_edges(f, "is-a")]
            for f in exp.get("no_family", []):
                if f in fams:
                    fails.append(f"{ex.name} is in {f}")
            stressed = {e.dst for e in store.out_edges(node, "stresses")}
            for r in exp.get("no_region", []):
                if r in stressed:
                    fails.append(f"{ex.name} stresses {r}")
            for p in exp.get("no_pattern", []):
                if p in ex.movement_patterns:
                    fails.append(f"{ex.name} has pattern {p}")
            for q in exp.get("no_equipment", []):
                if q in ex.equipment_required:
                    fails.append(f"{ex.name} needs {q}")
    if "note_contains" in exp and not any(exp["note_contains"] in n for n in plan["trace"]["notes"]):
        fails.append(f"no note containing {exp['note_contains']!r}")
    return fails


def trace_summary(plan: dict[str, Any]) -> dict[str, Any]:
    """The parts of the provenance trace a reader checks: what was read, what was filtered and why,
    the alternatives offered, the notes, and each item's reasons."""
    t = plan["trace"]
    return {
        "read": [f"{r['said']} -> {r['understood_as']} ({r['status']}, {r['method']})" for r in t["read"]],
        "restrictions": [
            f"{', '.join(r['regions'])}{' (' + r['side'] + ')' if r['side'] else ''} from {r['from']}"
            for r in t["restrictions"]
        ],
        "excluded": [
            {"reason": g["reason"], "rule": g["rule"], "count": len(g["exercises"]), "trusted": g["trusted"]}
            for g in t["excluded"]
        ],
        "alternatives": [f"{a['use']} instead of {a['instead_of']}" for a in t.get("alternatives", [])],
        "notes": t["notes"],
        "items": [
            {"name": i["name"], "sets": i["sets"], "why": i["why"], "counted_against": i["counted_against"]}
            for b in plan["blocks"]
            for i in b["items"]
        ],
    }


async def run_case(world: World, llm: RecordingLLM, case: dict[str, Any]) -> dict[str, Any]:
    exp = case["expect"]
    member = member_for(world, case)
    out: dict[str, Any] = {"id": case["id"], "channel": case.get("channel", "coach request"), "fails": []}
    sent_before = len(llm.sent)
    if case.get("surface", "generator") in ("generator", "both"):
        plan, blocked = None, False
        req = GenerateRequest(member_id=member.id, prompt=case["prompt"])
        async for ev in run(world, llm, req, member, "coach_01HXSAM"):
            if ev["event"] == "plan":
                plan = ev["plan"]
            elif ev["event"] == "blocked":
                blocked = True
            elif ev["event"] == "error":
                out["fails"].append(f"error: {ev['message']}")
        out["fails"] += plan_checks(world, plan, blocked, exp)
        out["plan"] = (
            {
                "minutes": plan["minutes_planned"],
                "items": [i["name"] for b in plan["blocks"] for i in b["items"]],
                "ms": plan["timings_ms"]["total"],
                "trace": trace_summary(plan),
            }
            if plan
            else ("blocked" if blocked else None)
        )
    if case.get("surface") in ("copilot", "both"):
        try:
            ans = await agent.ask(
                llm, world.settings.llm_model_main or "", world.context(member), case["question"]
            )
            out["answer"] = ans.text
            out["tools_used"] = ans.tools_used
            if not set(ans.tools_used) <= READ_TOOLS:
                out["fails"].append(f"unexpected tools {ans.tools_used}")
            for pat in exp.get("claims_not", []):
                # Text the answer quotes (an injected line it reports and ignores) is not its claim.
                unquoted = QUOTED.sub('"…"', ans.text)
                for sentence in re.split(r"(?<=[.!?])\s+|\n", unquoted):
                    if re.search(pat, sentence, re.IGNORECASE) and not NEGATION.search(sentence):
                        out["fails"].append(f"answer asserts /{pat}/: {sentence.strip()[:120]}")
            for pat in exp.get("answer_not", []):
                if re.search(pat, ans.text, re.IGNORECASE):
                    out["fails"].append(f"answer matched /{pat}/")
        except LLMError as exc:
            out["fails"].append(f"copilot error: {exc}")
    sent = "\n".join(llm.sent[sent_before:])
    for s in exp.get("prompt_never_contains", []):
        if s in sent:
            out["fails"].append(f"{s!r} reached the model")
    out["pass"] = not out["fails"]
    return out


async def main() -> int:
    world, llm = get_world(), RecordingLLM()
    suites = {
        "scenarios": yaml.safe_load((EVAL / "scenarios" / "cases.yaml").read_text()),
        "adversarial": yaml.safe_load((EVAL / "adversarial" / "cases.yaml").read_text()),
    }
    results = {name: [await run_case(world, llm, c) for c in cases] for name, cases in suites.items()}
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    (EVAL / "results" / "latest.json").write_text(json.dumps({"run_at": stamp, **results}, indent=1) + "\n")
    lines = [
        "# Evaluation results\n",
        f"Run {stamp} with the live model API, pipeline in-process. "
        f"Models: fast `{world.settings.llm_model_fast}`, "
        f"main `{world.settings.llm_model_main}`. Checks are deterministic (graph facts and regexes).\n",
    ]
    total = failed = 0
    for name, rows in results.items():
        lines += [f"\n## {name.capitalize()}\n", "| Case | Channel | Result | Detail |", "|---|---|---|---|"]
        for r in rows:
            total += 1
            failed += not r["pass"]
            detail = (
                "; ".join(r["fails"])
                if r["fails"]
                else (
                    "blocked, asked the coach"
                    if r.get("plan") == "blocked"
                    else f"{len(r['plan']['items'])} exercises, {r['plan']['minutes']} min"
                    if isinstance(r.get("plan"), dict)
                    else f"tools: {', '.join(dict.fromkeys(r.get('tools_used', []))) or 'none'}"
                )
            )
            lines.append(f"| {r['id']} | {r['channel']} | {'pass' if r['pass'] else 'FAIL'} | {detail} |")
    lines.append(f"\n{total - failed} of {total} passed. Full answers and plans: `eval/results/latest.json`.")
    (EVAL / "results" / "latest.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    render_traces()
    return 1 if failed else 0


def render_traces() -> None:
    """eval/results/traces.md: each drafted plan with its provenance and filtering trace."""
    data = json.loads((EVAL / "results" / "latest.json").read_text())
    prompts = {c["id"]: c["prompt"] for c in yaml.safe_load((EVAL / "scenarios" / "cases.yaml").read_text())}
    out = [
        "# Plans and their traces\n",
        f"From the eval run of {data['run_at']} (`latest.json`). "
        "Member: the fictional Jordan unless the case names another.\n",
    ]
    for r in data["scenarios"]:
        plan = r.get("plan")
        out.append(f"## {r['id']}\n\n> {prompts.get(r['id'], '')}\n")
        if not isinstance(plan, dict):
            out.append("Blocked: the injury mention couldn't be resolved, so the coach was asked.\n")
            continue
        t = plan["trace"]
        out.append(f"{len(plan['items'])} exercises, {plan['minutes']} min, {plan['ms']} ms.\n")
        out.append("| Exercise | Sets | Chosen because | Counted against |\n|---|---|---|---|")
        for i in t["items"]:
            out.append(
                f"| {i['name']} | {i['sets']} | {'; '.join(i['why']) or '-'} | "
                f"{'; '.join(i['counted_against']) or '-'} |"
            )
        out.append("\n**Request read:** " + ("; ".join(t["read"]) or "nothing specific") + "\n")
        out.append("**Restrictions:** " + ("; ".join(t["restrictions"]) or "none") + "\n")
        out.append("**Filtered out before drafting:**\n")
        for g in t["excluded"]:
            rule = f" (rule `{g['rule']}`)" if g["rule"] else ""
            flag = "" if g["trusted"] else " - unverified"
            out.append(f"- {g['reason']}{rule}: {g['count']} exercises{flag}")
        if t["alternatives"]:
            out.append("\n**Equivalent alternatives:** " + "; ".join(t["alternatives"]))
        if t["notes"]:
            out.append("\n**Notes:**\n" + "\n".join(f"- {n}" for n in t["notes"]))
        out.append("")
    (EVAL / "results" / "traces.md").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    if sys.argv[1:] == ["--render"]:
        render_traces()
        sys.exit(0)
    sys.exit(asyncio.run(main()))

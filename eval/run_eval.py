"""Run the generator scenarios and adversarial cases with the live model API; write eval/results/.

Usage: cd api && uv run python ../eval/run_eval.py
Needs ANTHROPIC_FUTURE_API_KEY, LLM_MODEL_FAST and LLM_MODEL_MAIN. Checks are deterministic
(graph facts and regexes), never a model grading a model. Every prompt sent to the model is
recorded in memory so the run can check what never reaches it; nothing is written but results.
Results hold the model's answers with any 24+ character span of the assessment's member text
(chat lines, captions, notes) replaced by a placeholder, because that text is not ours to
redistribute (NOTICE). `--redact` applies the same to the stored results without a model call.
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
REPO = EVAL.parent
MIN_SPAN = 24  # characters of member text that count as quoting it
PLACEHOLDER = "[member text]"
READ_TOOLS = {t["name"] for t in agent.TOOLS}
# A claim is let off only when one of these comes before it in the same clause: a negation
# ("I can't confirm the knee is healed"), a condition ("if the knee is healed") or an attribution
# ("the member says the knee is healed"). A negation elsewhere in the sentence doesn't count.
# "and" doesn't end a clause: in "a line says it's from the coach and that the restriction is
# lifted", both halves are what the line says.
NEGATION = re.compile(
    r"\b(not|no|nothing|none|neither|nor|never|cannot|can't|don't|doesn't|isn't|hasn't|haven't|"
    r"unconfirmed|unless|until|whether|if|claims?|claimed|says?|said|reports?|reported|according to)\b",
    re.I,
)
CLAUSE = re.compile(r"[,;:()\u2014\u2013]|\s-\s|\b(?:but|however|although|though|while|because|since|so)\b", re.I)


def asserts(pat: str, sentence: str) -> bool:
    """True when a clause of the sentence matches `pat` with no negation, condition or attribution
    before the match in that clause."""
    for clause in CLAUSE.split(sentence):
        for m in re.finditer(pat, clause or "", re.IGNORECASE):
            if not NEGATION.search(clause[: m.start()]):
                return True
    return False


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


def member_text(record: dict[str, Any]) -> list[str]:
    """The free text of a member record that results must not quote: chat, captions and notes."""
    out = [str(m.get("text") or "") for m in record.get("chat_history", [])]
    out += [
        str(a.get("caption") or "")
        for m in record.get("chat_history", [])
        for a in m.get("attachments") or []
    ]
    out += [str(i.get("notes") or "") for i in record.get("injuries", [])]
    out.append(str((record.get("preferences") or {}).get("notes") or ""))
    return [t for t in out if len(t) >= MIN_SPAN]


def our_text() -> str:
    """Text we wrote (rules, authored exercises, alignments). A span also found here is ours."""
    return "\n".join(p.read_text() for p in sorted((REPO / "kg").rglob("*.yaml")))


def leaked_spans(text: str, sources: list[str], ours: str = "") -> list[tuple[int, int, int]]:
    """(source index, start, length) of each maximal span of >= MIN_SPAN characters of a source
    that appears in `text`, skipping spans that start with text we wrote ourselves."""
    found = []
    for k, src in enumerate(sources):
        i = 0
        while i <= len(src) - MIN_SPAN:
            window = src[i : i + MIN_SPAN]
            if window in text and window not in ours:
                n = MIN_SPAN
                while i + n < len(src) and src[i : i + n + 1] in text:
                    n += 1
                found.append((k, i, n))
                i += n
            else:
                i += 1
    return found


def redact(value: Any, sources: list[str], ours: str = "") -> Any:
    """Replace quoted member text in every string of a results structure with PLACEHOLDER."""
    if isinstance(value, str):
        # Repeat until clean: replacing one span can leave an overlapping one whole.
        while leaks := leaked_spans(value, sources, ours):
            spans = sorted({sources[k][i : i + n] for k, i, n in leaks}, key=len, reverse=True)
            before = value
            for span in spans:
                value = value.replace(span, PLACEHOLDER)
            if value == before:
                break
        return value
    if isinstance(value, list):
        return [redact(v, sources, ours) for v in value]
    if isinstance(value, dict):
        return {k: redact(v, sources, ours) for k, v in value.items()}
    return value


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


def text_checks(what: str, text: str, exp: dict[str, Any]) -> list[str]:
    """claims_not: no unnegated sentence asserts it; answer_not: never appears; answer_has: must
    appear (each entry is a regex, matched case-insensitively)."""
    fails = []
    for pat in exp.get("claims_not", []):
        # Text the answer quotes (an injected line it reports and ignores) is not its claim.
        unquoted = QUOTED.sub('"…"', text)
        for sentence in re.split(r"(?<=[.!?])\s+|\n", unquoted):
            if asserts(pat, sentence):
                fails.append(f"{what} asserts /{pat}/: {sentence.strip()[:120]}")
    for pat in exp.get("answer_not", []):
        if re.search(pat, text, re.IGNORECASE):
            fails.append(f"{what} matched /{pat}/")
    for pat in exp.get("answer_has", []):
        if not re.search(pat, text, re.IGNORECASE):
            fails.append(f"{what} lacks /{pat}/")
    return fails


async def run_case(world: World, llm: RecordingLLM, case: dict[str, Any]) -> dict[str, Any]:
    exp = case["expect"]
    member = member_for(world, case)
    out: dict[str, Any] = {"id": case["id"], "channel": case.get("channel", "coach request"), "fails": []}
    sent_before = len(llm.sent)
    if case.get("surface", "generator") in ("generator", "both"):
        plan, blocked = None, False
        req = GenerateRequest(
            member_id=member.id,
            prompt=case["prompt"],
            cleared_low_impact=case.get("cleared_low_impact", []),
            confirmed_regions=case.get("confirmed_regions", []),
        )
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
            history = [agent.Turn(t["role"], t["text"]) for t in case.get("history", [])]
            ans = await agent.ask(
                llm, world.settings.llm_model_main or "", world.context(member), case["question"], history
            )
            out["answer"] = ans.text
            out["tools_used"] = ans.tools_used
            out["guarded"] = ans.guarded
            if not set(ans.tools_used) <= READ_TOOLS:
                out["fails"].append(f"unexpected tools {ans.tools_used}")
            for tool in exp.get("tools_include", []):
                if tool not in ans.tools_used:
                    out["fails"].append(f"didn't call {tool}")
            out["fails"] += text_checks("answer", ans.text, exp)
        except LLMError as exc:
            out["fails"].append(f"copilot error: {exc}")
    if case.get("surface") == "draft":
        try:
            draft = await agent.congratulation_draft(
                llm, world.settings.llm_model_main or "", world.context(member)
            )
            out["answer"] = draft["draft"] or ""
            out["fails"] += text_checks("draft", out["answer"], exp)
        except LLMError as exc:
            out["fails"].append(f"draft error: {exc}")
    sent = "\n".join(llm.sent[sent_before:])
    for s in exp.get("prompt_never_contains", []):
        if s in sent:
            out["fails"].append(f"{s!r} reached the model")
    out["pass"] = not out["fails"]
    return out


async def main(runs: int = 1) -> int:
    """Run every case `runs` times. A case passes only if it passes every run; the stored answers
    and plans are from the last run, and each failing run's reasons are kept."""
    world, llm = get_world(), RecordingLLM()
    suites = {
        "scenarios": yaml.safe_load((EVAL / "scenarios" / "cases.yaml").read_text()),
        "adversarial": yaml.safe_load((EVAL / "adversarial" / "cases.yaml").read_text()),
    }
    passes: dict[str, int] = {}
    failures: dict[str, list[str]] = {}
    results: dict[str, list[dict[str, Any]]] = {}
    for n in range(runs):
        results = {name: [await run_case(world, llm, c) for c in cases] for name, cases in suites.items()}
        for rows in results.values():
            for r in rows:
                passes[r["id"]] = passes.get(r["id"], 0) + bool(r["pass"])
                failures.setdefault(r["id"], []).extend(f"run {n + 1}: {f}" for f in r["fails"])
    for rows in results.values():
        for r in rows:
            r["runs_passed"] = f"{passes[r['id']]}/{runs}"
            r["pass"] = passes[r["id"]] == runs
            r["fails"] = failures[r["id"]]
    results = redact(results, assessment_text(), our_text())
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    (EVAL / "results" / "latest.json").write_text(
        json.dumps({"run_at": stamp, "runs": runs, **results}, indent=1) + "\n"
    )
    lines = [
        "# Evaluation results\n",
        f"Run {stamp} with the live model API, pipeline in-process, every case {runs} time(s). "
        f"Models: fast `{world.settings.llm_model_fast}`, "
        f"main `{world.settings.llm_model_main}`. Checks are deterministic (graph facts and regexes). "
        "A case passes only if it passed every run; details are from the last run.\n",
    ]
    total = failed = 0
    for name, rows in results.items():
        lines += [
            f"\n## {name.capitalize()}\n",
            "| Case | Channel | Runs passed | Result | Detail |",
            "|---|---|---|---|---|",
        ]
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
            lines.append(
                f"| {r['id']} | {r['channel']} | {r['runs_passed']} | {'pass' if r['pass'] else 'FAIL'} | {detail} |"
            )
    lines.append(
        f"\n{total - failed} of {total} passed in all {runs} run(s). "
        "Full answers and plans: `eval/results/latest.json`."
    )
    (EVAL / "results" / "latest.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    render_traces()
    return 1 if failed else 0


def assessment_text() -> list[str]:
    return member_text(json.loads((REPO / "data" / "member-context.json").read_text()))


def redact_stored() -> None:
    """Apply the redaction to results already on disk (no model call)."""
    sources, ours = assessment_text(), our_text()
    path = EVAL / "results" / "latest.json"
    path.write_text(json.dumps(redact(json.loads(path.read_text()), sources, ours), indent=1) + "\n")
    for name in ("latest.md", "traces.md"):
        md = EVAL / "results" / name
        md.write_text(redact(md.read_text(), sources, ours))


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
    if sys.argv[1:] == ["--redact"]:
        redact_stored()
        sys.exit(0)
    runs = int(sys.argv[2]) if sys.argv[1:2] == ["--runs"] else 1
    sys.exit(asyncio.run(main(runs)))

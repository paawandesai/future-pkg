"""Step 5: split candidates into warm-up / main / cool-down pools and fit a time budget.

The time budget is enforced here, after selection, so the model can never make a plan run long.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from coachkg.data import Exercise
from coachkg.generator.programming import Dose, Programming
from coachkg.generator.scoring import Scored

BlockName = Literal["warmup", "main", "cooldown"]
BLOCKS: tuple[BlockName, ...] = ("warmup", "main", "cooldown")


@dataclass
class Item:
    exercise: Exercise
    block: BlockName
    sets: int
    reps: int | None
    work_s: int | None
    rest_s: int
    each_side: bool
    seconds: int
    picked_by: Literal["selection", "fill"]


def pools(
    scored: list[Scored], prog: Programming, sizes: dict[BlockName, int]
) -> dict[BlockName, list[Scored]]:
    warm = set(prog.blocks.warmup.patterns)
    cool = set(prog.blocks.cooldown.patterns)
    out: dict[BlockName, list[Scored]] = {"warmup": [], "main": [], "cooldown": []}
    for s in scored:
        pats = set(s.exercise.movement_patterns)
        if pats & warm:
            out["warmup"].append(s)
        elif pats & cool:
            out["cooldown"].append(s)
        else:
            out["main"].append(s)
    # In the main block, focus matches come first when the request named a focus.
    out["main"].sort(key=lambda s: (not s.focus_match, -s.score, s.exercise.name))
    return {b: v[: sizes[b]] for b, v in out.items()}


def block_budgets(minutes: int, prog: Programming) -> dict[BlockName, int]:
    def edge(share: float, lo: float, hi: float) -> int:
        return int(round(min(hi, max(lo, minutes * share)) * 60))

    w = edge(prog.blocks.warmup.share, prog.blocks.warmup.min_minutes, prog.blocks.warmup.max_minutes)
    c = edge(prog.blocks.cooldown.share, prog.blocks.cooldown.min_minutes, prog.blocks.cooldown.max_minutes)
    return {"warmup": w, "main": max(0, minutes * 60 - w - c), "cooldown": c}


def make_item(ex: Exercise, block: BlockName, prog: Programming, sets: int | None = None) -> Item:
    if block == "main":
        dose: Dose = prog.blocks.main.dose_reps if ex.is_reps is not False else prog.blocks.main.dose_duration
    else:
        dose = getattr(prog.blocks, block).dose
    n = sets or dose.sets
    use_reps = dose.reps is not None and ex.is_reps is not False
    each_side = ex.laterality != "both"
    work = (dose.reps or 0) * prog.tempo_s if use_reps else float(dose.work_s or 30)
    seconds = n * work * (2 if each_side else 1) + (n - 1) * dose.rest_s + prog.transition_s
    return Item(
        ex,
        block,
        n,
        dose.reps if use_reps else None,
        None if use_reps else (dose.work_s or 30),
        dose.rest_s,
        each_side,
        int(round(seconds)),
        "selection",
    )


def _fit_block(
    b: BlockName, chosen: list[Exercise], pool: list[Scored], budget: int, prog: Programming
) -> list[Item]:
    items: list[Item] = []
    used = 0
    seen: set[str] = set()
    order = [(ex, "selection") for ex in chosen] + [(s.exercise, "fill") for s in pool]
    for ex, picked_by in order:
        if ex.id in seen:
            continue
        item = make_item(ex, b, prog)
        min_sets = prog.blocks.main.min_sets if b == "main" else item.sets
        while used + item.seconds > budget and item.sets > min_sets:
            item = make_item(ex, b, prog, item.sets - 1)
        if used + item.seconds <= budget:
            item.picked_by = "selection" if picked_by == "selection" else "fill"
            items.append(item)
            used += item.seconds
            seen.add(ex.id)
    return items


def top_up(items: list[Item], budget: int, prog: Programming) -> int:
    """Add one main-block set at a time, in plan order, up to `max_sets`, while it fits the budget.
    Only exercises already in the plan get sets, so nothing new is allowed. Returns sets added."""
    cap = prog.blocks.main.max_sets
    if not cap:
        return 0
    used = sum(i.seconds for i in items)
    added = 0
    grew = True
    while grew:
        grew = False
        for k, item in enumerate(items):
            if item.sets >= cap:
                continue
            bigger = make_item(item.exercise, "main", prog, item.sets + 1)
            if used - item.seconds + bigger.seconds <= budget:
                bigger.picked_by = item.picked_by
                used += bigger.seconds - item.seconds
                items[k] = bigger
                added += 1
                grew = True
    return added


def fit(
    chosen: dict[BlockName, list[Exercise]],
    pool: dict[BlockName, list[Scored]],
    budgets: dict[BlockName, int],
    prog: Programming,
    extra_sets: bool = True,
) -> tuple[dict[BlockName, list[Item]], int, dict[BlockName, int]]:
    """Take the selected exercises in order while they fit, then fill spare time by score, then
    (when `extra_sets`) add main-block sets up to `max_sets`. Returns the blocks, the sets added
    and the budgets as used (the main block takes what the warm-up and cool-down left)."""
    out = {b: _fit_block(b, chosen.get(b, []), pool[b], budgets[b], prog) for b in ("warmup", "cooldown")}
    # Time the warm-up and cool-down pools can't use (they are small after the filter) goes to the
    # main block rather than being left empty.
    spare = sum(budgets[b] - sum(i.seconds for i in out[b]) for b in ("warmup", "cooldown"))
    main_budget = budgets["main"] + max(0, spare)
    out["main"] = _fit_block("main", chosen.get("main", []), pool["main"], main_budget, prog)
    added = top_up(out["main"], main_budget, prog) if extra_sets else 0
    used_budgets: dict[BlockName, int] = {
        "warmup": sum(i.seconds for i in out["warmup"]),
        "main": main_budget,
        "cooldown": sum(i.seconds for i in out["cooldown"]),
    }
    return {b: out[b] for b in BLOCKS}, added, used_budgets

"""Run the comparison and print the report.

For each question, mode, and seed, run the agent once, collect the metrics,
and print an effect-size table, a per-mode summary, and a per-run table so
the skill vs subagent tradeoff, and whether it holds up above run-to-run
noise, is visible at a glance.
"""

from __future__ import annotations

import statistics
import sys
from collections.abc import Callable, Iterable

from .knowledge import QUESTIONS, Question
from .models import RunResult
from .runner import ResearchAgent

MODES = ("skill", "subagent")

# (label, extractor, print format) for the metrics the effect-size table
# compares between modes within each (capability, coupling) cell.
_METRICS: list[tuple[str, Callable[[RunResult], float], str]] = [
    ("total_tokens", lambda r: r.total_tokens, "{:.0f}"),
    ("main_ctx_peak", lambda r: r.main.peak_context_tokens, "{:.0f}"),
    ("latency_s", lambda r: r.latency_s, "{:.1f}"),
]


def run_experiment(
    agent: ResearchAgent,
    questions: Iterable[Question],
    modes: Iterable[str],
    seeds: int = 1,
    on_result: Callable[[list[RunResult]], None] | None = None,
) -> list[RunResult]:
    """Run every (question, mode, seed) combination.

    A long sweep (many seeds) can run for a while and can fail partway
    through a live API call. on_result, if given, is called with the
    accumulated results after every single run, so a caller can checkpoint
    progress to disk rather than lose everything on a mid-sweep crash.
    """
    questions = list(questions)
    modes = list(modes)
    total = len(questions) * len(modes) * seeds
    results: list[RunResult] = []
    for question in questions:
        for mode in modes:
            for seed in range(seeds):
                result = agent.run(question, mode, seed)
                results.append(result)
                print(
                    f"[{len(results)}/{total}] {result.capability}/{result.coupling} "
                    f"{result.question_id} {result.mode} seed={result.seed} "
                    f"{'ok' if result.correct else 'WRONG'} "
                    f"{result.total_tokens}tok {result.latency_s:.1f}s",
                    file=sys.stderr,
                )
                if on_result is not None:
                    on_result(results)
    return results


def _format_runs(results: list[RunResult]) -> str:
    header = (
        f"{'capability':<11}{'coupling':<9}{'question':<9}{'mode':<10}{'seed':<5}"
        f"{'ok':<4}{'main ctx pk':<13}{'main tok':<10}{'sub tok':<9}"
        f"{'total tok':<11}{'calls':<7}{'latency':<9}"
    )
    lines = [header, "-" * len(header)]
    for r in results:
        calls = f"{r.main.api_calls}+{r.sub.api_calls}"
        lines.append(
            f"{r.capability:<11}{r.coupling:<9}{r.question_id:<9}{r.mode:<10}{r.seed:<5}"
            f"{('yes' if r.correct else 'NO'):<4}"
            f"{r.main.peak_context_tokens:<13}{r.main.total_tokens:<10}"
            f"{r.sub.total_tokens:<9}{r.total_tokens:<11}{calls:<7}"
            f"{r.latency_s:>6.1f}s"
        )
    return "\n".join(lines)


def _format_summary(results: list[RunResult]) -> str:
    header = (
        f"{'mode':<10}{'runs':<6}{'accuracy':<10}"
        f"{'avg main ctx pk':<17}{'avg total tok':<15}{'avg latency':<12}"
    )
    lines = [header, "-" * len(header)]
    for mode in MODES:
        runs = [r for r in results if r.mode == mode]
        if not runs:
            continue
        n = len(runs)
        accuracy = sum(1 for r in runs if r.correct) / n
        avg_peak = sum(r.main.peak_context_tokens for r in runs) / n
        avg_total = sum(r.total_tokens for r in runs) / n
        avg_latency = sum(r.latency_s for r in runs) / n
        lines.append(
            f"{mode:<10}{n:<6}{accuracy:<10.0%}"
            f"{avg_peak:<17.0f}{avg_total:<15.0f}{avg_latency:>8.1f}s"
        )
    return "\n".join(lines)


def _cohens_d(a: list[float], b: list[float]) -> float | None:
    """Pooled-sd effect size for mean(a) - mean(b), or None below n=2 per side."""
    if len(a) < 2 or len(b) < 2:
        return None
    pooled_var = (
        (len(a) - 1) * statistics.variance(a) + (len(b) - 1) * statistics.variance(b)
    ) / (len(a) + len(b) - 2)
    pooled_std = pooled_var**0.5
    if pooled_std == 0:
        return None
    return (statistics.mean(a) - statistics.mean(b)) / pooled_std


def _mean_sd(values: list[float], fmt: str) -> str:
    if not values:
        return "n/a"
    mean = fmt.format(statistics.mean(values))
    if len(values) < 2:
        return mean
    return f"{mean} +/- {fmt.format(statistics.stdev(values))}"


def _format_cell_effects(results: list[RunResult]) -> str:
    """Skill vs subagent mean, stdev, and Cohen's d per (capability, coupling) cell.

    This is the number that answers "is the effect measurable above noise":
    a |d| that holds up as more seeds are added is signal, not a fluke run.
    """
    cells = sorted({(r.capability, r.coupling) for r in results})
    lines: list[str] = []
    for capability, coupling in cells:
        cell = [
            r for r in results if r.capability == capability and r.coupling == coupling
        ]
        skill = [r for r in cell if r.mode == "skill"]
        subagent = [r for r in cell if r.mode == "subagent"]
        lines.append(
            f"{capability} / {coupling}  (skill n={len(skill)}, subagent n={len(subagent)})"
        )
        lines.append(f"  {'metric':<15}{'skill':<20}{'subagent':<20}{'cohens d':<10}")
        for name, metric, fmt in _METRICS:
            a = [metric(r) for r in skill]
            b = [metric(r) for r in subagent]
            d = _cohens_d(a, b)
            d_str = f"{d:+.2f}" if d is not None else "n/a"
            lines.append(
                f"  {name:<15}{_mean_sd(a, fmt):<20}{_mean_sd(b, fmt):<20}{d_str:<10}"
            )
        skill_acc = f"{sum(r.correct for r in skill)}/{len(skill)}" if skill else "n/a"
        sub_acc = (
            f"{sum(r.correct for r in subagent)}/{len(subagent)}" if subagent else "n/a"
        )
        lines.append(f"  {'accuracy':<15}{skill_acc:<20}{sub_acc:<20}")
        lines.append("")
    lines.append(
        "Rule of thumb: |cohen's d| >= 0.8 is a conventionally large effect. "
        "With few seeds, treat these as directional until n grows."
    )
    return "\n".join(lines)


def format_report(results: list[RunResult]) -> str:
    return (
        "Effect size by cell\n"
        f"{_format_cell_effects(results)}\n\n"
        "Per-mode summary\n"
        f"{_format_summary(results)}\n\n"
        "Per-run metrics\n"
        f"{_format_runs(results)}\n"
    )


def default_questions() -> list[Question]:
    return list(QUESTIONS)

"""Run the comparison and print the report.

For each question and each requested mode, run the agent once, collect the
metrics, and print a per-run table plus a per-mode summary so the skill vs
subagent tradeoff is visible at a glance.
"""

from __future__ import annotations

from collections.abc import Iterable

from .knowledge import QUESTIONS, Question
from .models import RunResult
from .runner import ResearchAgent

MODES = ("skill", "subagent")


def run_experiment(
    agent: ResearchAgent,
    questions: Iterable[Question],
    modes: Iterable[str],
) -> list[RunResult]:
    results: list[RunResult] = []
    for question in questions:
        for mode in modes:
            results.append(agent.run(question, mode))
    return results


def _format_runs(results: list[RunResult]) -> str:
    header = (
        f"{'question':<9}{'hops':<5}{'mode':<10}{'ok':<4}"
        f"{'main ctx pk':<13}{'main tok':<10}{'sub tok':<9}"
        f"{'total tok':<11}{'calls':<7}{'latency':<9}"
    )
    lines = [header, "-" * len(header)]
    for r in results:
        calls = f"{r.main.api_calls}+{r.sub.api_calls}"
        lines.append(
            f"{r.question_id:<9}{r.hops:<5}{r.mode:<10}"
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


def format_report(results: list[RunResult]) -> str:
    return (
        "Per-run metrics\n"
        f"{_format_runs(results)}\n\n"
        "Per-mode summary\n"
        f"{_format_summary(results)}\n"
    )


def default_questions() -> list[Question]:
    return list(QUESTIONS)

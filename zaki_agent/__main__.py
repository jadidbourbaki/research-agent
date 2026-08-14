"""CLI entry point.

Examples:
    uv run python -m zaki_agent
    uv run python -m zaki_agent --mode skill
    uv run python -m zaki_agent --question q5 --model claude-opus-4-8
    uv run python -m zaki_agent --pilot --seeds 30 --out results/pilot-sweep.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config, knowledge
from .experiment import MODES, default_questions, format_report, run_experiment
from .models import RunResult
from .runner import ResearchAgent


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="zaki_agent",
        description="Compare skill vs subagent designs on the same problem.",
    )
    parser.add_argument(
        "--mode",
        choices=(*MODES, "both"),
        default="both",
        help="Which design to run (default: both).",
    )
    question_group = parser.add_mutually_exclusive_group()
    question_group.add_argument(
        "--question",
        default=None,
        help="Run a single question by id (e.g. q5). Default: all.",
    )
    question_group.add_argument(
        "--pilot",
        action="store_true",
        help=(
            "Run only the Phase 0 pilot cell design: one low- and one "
            f"high-coupling task per capability ({', '.join(knowledge.PILOT_QUESTION_IDS)})."
        ),
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=1,
        help="Independent repeats per (question, mode) cell, to sample run-to-run variance (default: 1).",
    )
    parser.add_argument(
        "--model",
        default=config.default_model(),
        help=f"Model id (default: {config.default_model()}).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Also write the report to this path (e.g. results/pilot-sweep.md).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.pilot:
        questions = knowledge.pilot_questions()
    else:
        questions = default_questions()
        if args.question is not None:
            questions = [q for q in questions if q.id == args.question]
            if not questions:
                print(f"No question with id {args.question!r}", file=sys.stderr)
                return 2

    modes = MODES if args.mode == "both" else (args.mode,)

    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)

    def checkpoint(results: list[RunResult]) -> None:
        # Overwrites --out after every run, so a mid-sweep crash still
        # leaves a report covering everything completed so far.
        if args.out is not None:
            args.out.write_text(format_report(results))

    agent = ResearchAgent(model=args.model)
    results = run_experiment(
        agent, questions, modes, seeds=args.seeds, on_result=checkpoint
    )
    report = format_report(results)
    print(report)

    if args.out is not None:
        print(f"Wrote {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

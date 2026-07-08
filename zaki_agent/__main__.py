"""CLI entry point.

Examples:
    uv run python -m zaki_agent
    uv run python -m zaki_agent --mode skill
    uv run python -m zaki_agent --question q5 --model claude-opus-4-8
"""

from __future__ import annotations

import argparse
import sys

from . import config
from .experiment import MODES, default_questions, format_report, run_experiment
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
    parser.add_argument(
        "--question",
        default=None,
        help="Run a single question by id (e.g. q5). Default: all.",
    )
    parser.add_argument(
        "--model",
        default=config.default_model(),
        help=f"Model id (default: {config.default_model()}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    questions = default_questions()
    if args.question is not None:
        questions = [q for q in questions if q.id == args.question]
        if not questions:
            print(f"No question with id {args.question!r}", file=sys.stderr)
            return 2

    modes = MODES if args.mode == "both" else (args.mode,)

    agent = ResearchAgent(model=args.model)
    results = run_experiment(agent, questions, modes)
    print(format_report(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

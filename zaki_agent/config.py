"""Model id and run limits, overridable from the environment."""

from __future__ import annotations

import os

# Claude Haiku 4.5. Cheap and fast, which suits sweeping the same problem many
# times. Override with --model or the ZAKI_AGENT_MODEL env var.
DEFAULT_MODEL = "claude-haiku-4-5"

# Answers to this problem are short, so a small output cap is plenty.
MAX_TOKENS = 2048

# A guard on the agentic loop so a confused run cannot spin forever.
MAX_TURNS = 12


def default_model() -> str:
    return os.environ.get("ZAKI_AGENT_MODEL", DEFAULT_MODEL)

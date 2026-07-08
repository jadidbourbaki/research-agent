"""Token accounting and per-run results.

Usage separates the main agent's context from any subagent context so the
report can show where the tokens and the context growth actually land.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class _AnthropicUsage(Protocol):
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int | None
    cache_creation_input_tokens: int | None


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    api_calls: int = 0
    # The largest single-request context the agent ever held. This is the
    # headline "how big did the window get" number.
    peak_context_tokens: int = 0

    def add(self, usage: _AnthropicUsage) -> None:
        cache_read = usage.cache_read_input_tokens or 0
        cache_creation = usage.cache_creation_input_tokens or 0
        context = usage.input_tokens + cache_read + cache_creation

        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.cache_read_tokens += cache_read
        self.cache_creation_tokens += cache_creation
        self.api_calls += 1
        self.peak_context_tokens = max(self.peak_context_tokens, context)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class RunResult:
    question_id: str
    hops: int
    mode: str
    answer: str
    correct: bool
    latency_s: float
    main: Usage = field(default_factory=Usage)
    sub: Usage = field(default_factory=Usage)
    sub_calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.main.total_tokens + self.sub.total_tokens

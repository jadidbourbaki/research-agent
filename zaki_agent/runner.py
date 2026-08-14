"""The two designs under study, parametrized over capabilities.

Both modes run the SDK's tool runner, which drives the tool-use loop for us.
For a given question's capability (see CAPABILITIES), they differ only in
where that capability's tool runs:

- skill mode gives the main agent the capability's tool and skill prompt
  inline, so it reads the underlying data in its own context.
- subagent mode gives the main agent a lookup tool that spawns a subagent with
  a fresh context, running the same capability. The subagent reads the data
  and returns a short answer, so the raw data never enters the main context.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import anthropic
from anthropic import beta_tool
from anthropic.types.beta import BetaMessage

from . import config, knowledge
from .models import RunResult, Usage

# Shared lookup instructions. In skill mode they go into the main agent's
# system prompt. In subagent mode they are the subagent's system prompt.
LOOKUP_SKILL = (
    "You answer factual questions using only the provided document collection. "
    "Use the search_documents tool to find relevant documents, read them, and "
    "chain facts across documents when a question needs more than one step. Do "
    "not rely on prior knowledge, the entities exist only in these documents. "
    "When you have the answer, reply with the answer alone and nothing else."
)

METRICS_SKILL = (
    "You answer questions about company revenue using the query_revenue tool. "
    "Call it with a company name for that company's figures, or with an empty "
    "string to get every company's figures when a question requires comparing "
    "across companies. Do not rely on prior knowledge, these figures exist "
    "only in this tool's data. When you have the answer, reply with the answer "
    "alone and nothing else."
)

# Subagent mode: the coordinator has no data access of its own, whatever the
# question's capability. It must delegate everything through the lookup tool.
COORDINATOR_SYSTEM = (
    "You are a research coordinator answering a question that requires one or "
    "more factual lookups. You have no knowledge of your own about the entities "
    "in the question, and no data access other than the lookup tool. Never "
    "answer from a guess: use the lookup tool for each self-contained factual "
    "question, then combine the results. When a question is multi-hop, look up "
    "one fact, then use it to phrase the next lookup. When a question requires "
    "comparing several entities, delegate a question that covers all of them, "
    "or delegate each one separately, whichever is more natural. When you have "
    "the answer, reply with the answer alone and nothing else."
)

# For the Stage A no-tools baseline filter (see validate_tasks.py): if this
# gets a synthetic-world question right, the task is answerable by guessing
# or memorization, not by the retrieval it's meant to require.
BASELINE_SYSTEM = (
    "Answer the question if you know it. If you do not know the answer, say "
    '"I don\'t know" and nothing else. Never guess.'
)


@beta_tool
def search_documents(query: str) -> str:
    """Search the documents and return the most relevant ones in full.

    Args:
        query: Keywords describing the fact you are looking for.
    """
    return knowledge.search_documents(query)


@beta_tool
def query_revenue(company: str) -> str:
    """Look up a company's annual revenue figures.

    Args:
        company: Company name to look up, or an empty string to get every
            company's figures for comparison.
    """
    return knowledge.query_revenue(company)


@dataclass(frozen=True)
class Capability:
    name: str
    skill_prompt: str
    tool: object


CAPABILITIES = {
    "lookup": Capability("lookup", LOOKUP_SKILL, search_documents),
    "metrics": Capability("metrics", METRICS_SKILL, query_revenue),
}


def _text_of(message: BetaMessage | None) -> str:
    if message is None:
        return "No answer produced."
    return "".join(
        block.text for block in message.content if block.type == "text"
    ).strip()


class ResearchAgent:
    def __init__(self, model: str, client: anthropic.Anthropic | None = None) -> None:
        self.model = model
        self.client = client or anthropic.Anthropic()

    def _drive(
        self,
        system: str,
        prompt: str,
        tools: list,
        usage: Usage,
    ) -> str:
        """Run the tool runner to completion, tallying usage on every turn."""
        runner = self.client.beta.messages.tool_runner(
            model=self.model,
            max_tokens=config.MAX_TOKENS,
            max_iterations=config.MAX_TURNS,
            system=system,
            tools=tools,
            messages=[{"role": "user", "content": prompt}],
        )
        final: BetaMessage | None = None
        for message in runner:
            usage.add(message.usage)
            final = message
        return _text_of(final)

    def _run_subagent(
        self, capability: Capability, sub_question: str, sub_usage: Usage
    ) -> str:
        return self._drive(
            capability.skill_prompt, sub_question, [capability.tool], sub_usage
        )

    def run_baseline(self, prompt: str) -> str:
        """Answer with no tools at all, for the Stage A no-tools pre-filter."""
        return self._drive(BASELINE_SYSTEM, prompt, [], Usage())

    def run(self, question: knowledge.Question, mode: str, seed: int = 0) -> RunResult:
        main_usage = Usage()
        sub_usage = Usage()
        sub_calls = 0
        start = time.monotonic()
        capability = CAPABILITIES[question.capability]

        if mode == "skill":
            system = (
                f"{capability.skill_prompt}\n\nThe question may require several steps."
            )
            answer = self._drive(system, question.prompt, [capability.tool], main_usage)
        elif mode == "subagent":

            @beta_tool
            def lookup(sub_question: str) -> str:
                """Delegate one self-contained factual question to a research
                assistant that has access to the data needed to answer it.

                Args:
                    sub_question: One self-contained factual question.
                """
                nonlocal sub_calls
                sub_calls += 1
                return self._run_subagent(capability, sub_question, sub_usage)

            answer = self._drive(
                COORDINATOR_SYSTEM, question.prompt, [lookup], main_usage
            )
        else:
            raise ValueError(f"unknown mode: {mode!r}, expected 'skill' or 'subagent'")

        latency = time.monotonic() - start
        return RunResult(
            question_id=question.id,
            capability=question.capability,
            coupling=question.coupling,
            hops=question.hops,
            mode=mode,
            seed=seed,
            answer=answer,
            correct=knowledge.is_correct(answer, question.answer),
            latency_s=latency,
            main=main_usage,
            sub=sub_usage,
            sub_calls=sub_calls,
        )

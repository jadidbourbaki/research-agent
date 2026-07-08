"""The two designs under study.

Both modes run the SDK's tool runner, which drives the tool-use loop for us.
They differ only in the tool the main agent is given and where the lookup work
runs:

- skill mode gives the main agent the search_documents tool and the lookup
  instructions inline, so it reads documents in its own context.
- subagent mode gives the main agent a lookup tool that spawns a subagent with
  a fresh context. The subagent reads documents and returns a short answer, so
  the document text never enters the main context.
"""

from __future__ import annotations

import time

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

# Subagent mode: the coordinator has no document access of its own.
COORDINATOR_SYSTEM = (
    "You are a research coordinator answering a question that requires one or "
    "more factual lookups. You do not have direct access to any documents. Use "
    "the lookup tool for each single, self-contained factual question, then "
    "combine the results. When a question is multi-hop, look up one fact, then "
    "use it to phrase the next lookup. When you have the answer, reply with the "
    "answer alone and nothing else."
)


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

    def _run_subagent(self, sub_question: str, sub_usage: Usage) -> str:
        @beta_tool
        def search_documents(query: str) -> str:
            """Search the documents and return the most relevant ones in full.

            Args:
                query: Keywords describing the fact you are looking for.
            """
            return knowledge.search_documents(query)

        return self._drive(LOOKUP_SKILL, sub_question, [search_documents], sub_usage)

    def run(self, question: knowledge.Question, mode: str) -> RunResult:
        main_usage = Usage()
        sub_usage = Usage()
        sub_calls = 0
        start = time.monotonic()

        if mode == "skill":

            @beta_tool
            def search_documents(query: str) -> str:
                """Search the documents and return the most relevant ones in full.

                Args:
                    query: Keywords describing the fact you are looking for.
                """
                return knowledge.search_documents(query)

            system = f"{LOOKUP_SKILL}\n\nThe question may require several steps."
            answer = self._drive(
                system, question.prompt, [search_documents], main_usage
            )
        elif mode == "subagent":

            @beta_tool
            def lookup(sub_question: str) -> str:
                """Delegate one self-contained factual lookup to a research
                assistant that has access to the documents.

                Args:
                    sub_question: One self-contained factual question.
                """
                nonlocal sub_calls
                sub_calls += 1
                return self._run_subagent(sub_question, sub_usage)

            answer = self._drive(
                COORDINATOR_SYSTEM, question.prompt, [lookup], main_usage
            )
        else:
            raise ValueError(f"unknown mode: {mode!r}, expected 'skill' or 'subagent'")

        latency = time.monotonic() - start
        return RunResult(
            question_id=question.id,
            hops=question.hops,
            mode=mode,
            answer=answer,
            correct=knowledge.is_correct(answer, question.answer),
            latency_s=latency,
            main=main_usage,
            sub=sub_usage,
            sub_calls=sub_calls,
        )

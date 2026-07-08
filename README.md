# zaki-agent

A small harness for studying one question: when an agent needs a reusable
capability, is it better to give the agent that capability inline (a **skill**)
or to delegate it to a **subagent** with its own context?

Both are run against the same problem so the difference in context growth,
token cost, and accuracy reflects the design choice and nothing else.

## The problem

A main agent answers multi-hop questions over a small, synthetic document
collection. Answering "what is the capital of the country where Aurelia Systems
is headquartered?" takes three lookups: the company's city, the city's country,
and the country's capital. The reusable capability is a single-fact document
lookup.

The world is fictional so the agent cannot answer from memory. It has to
retrieve and chain facts, which is exactly the behavior we want to measure.

## The two designs

- **skill mode**: the main agent has the `search_documents` tool and the lookup
  instructions in its own system prompt. It reads every document in its own
  context, so the context grows with the evidence it gathers.
- **subagent mode**: the main agent has a `lookup` tool. Each call spawns a
  subagent with a fresh context that reads the documents and returns a short
  answer. The document text stays in the subagent, so the main context stays
  lean, at the cost of an extra round trip and possible loss of detail.

The only thing that differs between the modes is where the lookup runs. See
`zaki_agent/runner.py`.

## What it measures

Per run: main-agent peak context, main tokens, subagent tokens, total tokens,
API calls (`main+sub`), whether the answer was correct, and wall-clock latency.
Then a per-mode summary with accuracy and averages.

## Setup

```bash
uv sync
```

Credentials are read from the environment the way the `anthropic` SDK resolves
them (`ANTHROPIC_API_KEY`, or an `ant auth login` profile).

## Run

```bash
just run                              # all questions, both modes
just run --mode skill                 # skill mode only
just run --mode subagent              # subagent mode only
just run --question q5                # one question, both modes
just run --model claude-opus-4-8      # a stronger model for a harder sweep
```

The default model is Claude Haiku 4.5, which is cheap and fast enough to sweep
the same problem many times. Override it with `--model` or the `ZAKI_AGENT_MODEL`
environment variable.

## Results

Saved runs live in `results/`. See
[results/initial-sweep.md](results/initial-sweep.md) for a first full sweep on
Claude Haiku 4.5.

## Develop

```bash
just check    # ruff + ty + pytest
just fmt      # format and autofix
```

## Extending the experiment

- Add questions or documents in `zaki_agent/knowledge.py`.
- Add a mode in `zaki_agent/runner.py` and list it in `experiment.MODES`.
- The design deliberately keeps the search tool and the lookup instructions
  shared, so a third design can reuse them.

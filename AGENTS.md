# AGENTS.md

Guidance for AI agents working on the zaki-agent codebase. The CLAUDE.md
symlink resolves to this file. Read top-to-bottom on first session. The Python
practices here are adapted from the orla project's AGENTS.md.

## Project context

zaki-agent is a small experiment harness. A main agent solves a simple
multi-hop question-answering problem over a fixed document collection, and the
same problem can be run two ways:

- **skill mode**: the lookup capability lives in the main agent's own context.
  The main agent has a `search_documents` tool and the lookup instructions
  inline, so all document text and search reasoning accumulate in one context.
- **subagent mode**: the main agent delegates each single-fact lookup to a
  subagent that runs in a fresh context. The subagent reads the documents and
  returns a short answer. Document text and search reasoning stay out of the
  main context.

The point is to measure the tradeoffs between the two, context growth, token
cost, and accuracy, on the same task. See `README.md` for the run commands and
`zaki_agent/knowledge.py` for the problem itself.

The codebase is small and uniformly Python. It talks to Claude through the
official `anthropic` SDK.

## Quality gate

Before declaring any change complete, run:

```bash
just check
```

That runs `ruff` (lint), `ty` (type check), and `pytest`. If it does not pass
locally, the work is not done.

Individual recipes:

```bash
just run ...     # run the experiment (pass CLI args after run)
just fmt         # ruff format + ruff check --fix
just lint        # ruff check
just typecheck   # ty check
just test        # pytest
just             # list recipes
```

## Repository layout

```
zaki_agent/
  __main__.py     CLI entry point
  config.py       model id and run limits
  knowledge.py    the document collection, the questions, and the search tool
  models.py       Usage accumulator and RunResult dataclasses
  runner.py       the tool runner and the two modes (skill, subagent)
  experiment.py   run the comparison and print the report
tests/            pytest coverage for the deterministic pieces
results/          saved experiment runs
```

## Writing prose

These rules apply to all prose in the repo: README, docs, commit message
bodies, code comments. They were carried over from the orla maintainer's stated
preference and must be honored.

### Hard rules

- **No em-dashes.** The character does not appear in prose. If you would use
  one, split into two sentences or use a comma. The same goes for en-dashes.
- **No semicolons in prose.** Use a period and start a new sentence.
- **No unnecessary parentheses.** A parenthetical aside that pauses the reader
  for a thought you could have put in its own sentence should go in its own
  sentence. Parens are fine for genuine clarifications such as an abbreviation
  on first use.
- **No ASCII diagrams in prose.** Describe relationships in words. A layout
  block like the repository tree above is fine.
- **No emoji** unless the user explicitly asks for them.

### Soft rules

- Write short, direct sentences. If a sentence has more than one comma,
  consider whether it should be two sentences.
- Lead with the noun, not the qualifier.
- Define jargon on first use.

## Writing comments

The "Writing prose" rules apply, plus:

- **Default to writing no comment.** A well-named identifier and a short
  function explain themselves. Comment only when the WHY is non-obvious: a
  hidden constraint, a subtle invariant, behavior that would surprise a reader.
- **Don't describe what the code does.** The code does that.
- **Don't reference the past or the PR.** Comments describe the present state.
- **One-paragraph module docstring** at the top of each module. State what the
  module is for and, for the run scripts, how to invoke it.
- A function docstring earns its place only when the contract is non-obvious.

## Python style

The toolchain is Astral's, and it is not optional.

- **uv** for environments and dependencies. Use `uv add` to add a dependency,
  `uv lock` to resolve, `uv run` to execute inside the project environment.
- **ruff** for both linting and formatting. One tool for both.
- **ty** for type checking. It is Astral's checker and still young, so expect
  rough edges, but it is the house checker. Do not reach for mypy or pyright.
- **just** for task running.

### Project layout and dependencies

- Runtime dependencies go in `[project].dependencies`. Development tools go in
  `[dependency-groups].dev` per PEP 735.
- Pin exact versions with `==` and commit `uv.lock`. This is an app you run,
  not a library someone imports, so reproducibility beats flexibility.
- The lockfile is committed and never hand-edited. uv owns it.

### Types

Type every function signature, both parameters and return. `ty check` runs in
`just check`, so an untyped surface is a failing build.

- Put `from __future__ import annotations` at the top of every module.
- Use built-in generics, `list[int]` and `dict[str, T]`, not `typing.List`.
  Use `X | None`, not `Optional[X]`.
- Model structured data that crosses a boundary with a dataclass. Do not pass
  bare dicts whose shape lives only in your head.

### Naming

- `snake_case` for functions and variables, `PascalCase` for classes,
  `UPPER_SNAKE` for module constants. A single leading underscore marks a name
  module-private.
- Do not uppercase acronyms the way Go does. PEP 8 wins here.

### Errors

- Raise exceptions. Do not return a sentinel value to signal failure.
- Catch narrowly. A broad `except Exception` belongs only at a top-level
  boundary where you log and carry on. A bare `except:` is never correct.
- When you re-raise with new context, use `raise ... from err`.

### Don't reinvent the wheel

Prefer something already built, the standard library or a well-maintained
dependency, over code you write yourself. Reach for your own implementation
only when nothing fits. In particular, use the `anthropic` SDK's own helpers
and types rather than hand-rolling request or response handling.

## Writing tests

Use `pytest`. Cover the deterministic pieces: the document search, the answer
grading, and the integrity of the question set. Do not write tests that call
the live API in the default `just check` run. Name tests `test_<subject>_
<scenario>` so the scenario reads as a clause. Test the happy path and every
branch that returns an error or an empty result.

## Talking to Claude

- Use the official `anthropic` SDK. Construct a bare `anthropic.Anthropic()`
  client so it resolves credentials from the environment.
- The model id is configurable through `zaki_agent/config.py` and the
  `--model` flag. The default is Claude Haiku 4.5 (`claude-haiku-4-5`).
- Keep the two modes symmetric. The only thing that should differ between skill
  mode and subagent mode is where the lookup capability runs, so that the
  measured differences reflect that choice and nothing else.

## Commit messages

[Conventional commits](https://www.conventionalcommits.org/en/v1.0.0/), one
sentence each, no body unless absolutely necessary.

Rules:

- One sentence subject. Lowercase the type and the first word after the colon
  unless that first word is a proper noun or acronym.
- **No `Co-Authored-By: Claude` trailer.** Ever. Even when the user has
  authorized commits in advance.
- Do not amend or rewrite published commits without explicit user consent.

## Git practices

- Use whatever git identity the user has configured.
- Don't commit or push without an explicit in-conversation ask.
- Before any destructive operation, confirm with the user.

## Working with the user

- Default to terse. Lead with the result, then the details if asked.
- Match the scope of your changes to what the user asked. A bug fix does not
  get a free refactor of the surrounding code.
- When you spot a side-effect the user didn't ask for, name it and ask before
  doing it.

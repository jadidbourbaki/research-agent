default:
    @just --list

# Run the experiment. Pass CLI args after `run`, e.g. `just run --mode skill`.
run *ARGS:
    uv run python -m zaki_agent {{ARGS}}

fmt:
    uv run ruff format .
    uv run ruff check --fix .

lint:
    uv run ruff check .

typecheck:
    uv run ty check

test:
    uv run pytest

# The same read-only trio CI would run.
check: lint typecheck test

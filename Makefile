.PHONY: install lint fmt test test-data check run

install:
	uv sync --locked

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest -q

test-data:
	uv run pytest -q -m data

# The one command CI runs: lint + tests. Data tests skip themselves when data/ is missing.
check: lint test

run:
	uv run uvicorn app.main:app --reload

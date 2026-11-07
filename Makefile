.PHONY: install lint fmt test test-data check run submission-zip

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

# Source zip for the submission form: tracked files at HEAD, plus the accuracy files the brief asks
# for as separate files. Those are run output from out/ (gitignored), never committed.
submission-zip:
	mkdir -p dist
	git archive --format=zip --prefix=kaista/ -o dist/kaista-submission.zip HEAD
	uv run python -c "import zipfile; z = zipfile.ZipFile('dist/kaista-submission.zip', 'a'); [z.write('out/' + f, 'results/' + f) for f in ('3074_results.csv', 'terrestrial_findings.json', 'terrestrial_trends.csv', 'TERRESTRIAL.md')]; z.close()"

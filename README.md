# IFIC Triage (working title)

Since AI Hackathon 2026 · Challenge: Traficom, "Saving Earth from Space Interferers Using Radio Frequencies" · Team: Janne Rosama (solo)

## Problem

Every two weeks ITU publishes a BR IFIC with hundreds of new satellite filings. A Traficom specialist has to find the ones that may affect Finnish radio use, check them against Finnish frequency data and write to the administration behind them. Space IFIC 3074 alone has 196 notices and 95 865 frequency rows, and the check is done by hand.

## Solution

A deterministic triage pipeline that shows its work. It reads one IFIC package and derives the protected bands from Traficom's frequencies-of-interest table. It then keeps the space-to-Earth notices that overlap those bands and can be seen from Finland, and computes an upper-bound power flux-density (PFD) against the ITU Radio Regulations Article 21, Table 21-4 limit. Every notice gets a case card with the source rows, the calculation, the Finnish allocation from Regulation M4, the missing data and one question for the other administration. The queue shows the 20 most urgent cards. The accuracy file covers all 196 notices. A human decides.

The language model only writes the prose: the card summary and the draft letter. Every number comes from code.

_Screenshot: funnel and one case card._

## Demo

- Live: _<submission URL>_
- Video (~2 min): _<YouTube link>_

## Run it

```bash
sudo apt install mdbtools          # mdb-export reads the IFIC Access database
uv sync
cp <path>/Traficom_SinceAI_Frequencies_of_interest_v05112026.xlsx data/   # from the Since AI platform
uv run python scripts/fetch_data.py   # downloads IFIC 3074 and the M4 table, converts everything to CSV
uv run pytest
cp .env.example .env               # LLM for the prose only: LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
uv run uvicorn app.main:app --reload
# http://localhost:8000
```

### Develop

Needs [uv](https://docs.astral.sh/uv/) and `make`; uv installs Python 3.11+ itself if missing.

```bash
make install     # uv sync --locked
make check       # lint + tests; the same command CI runs (.github/workflows/ci.yml)
make lint        # ruff check + ruff format --check
make fmt         # fix lint and formatting
make test        # pytest -q; tests marked @pytest.mark.data skip when data/ is missing
make test-data   # only the tests that need the real data
make run         # uvicorn on http://localhost:8000
```

Layout: `app/` source, one module per feature (`app/<feature>.py`) with its own test file `tests/test_<feature>.py`; `scripts/` data fetch; `tests/fixtures/` small committed test data; `data/` and `out/` are local only and ignored. Configuration lives in `pyproject.toml` (dependencies, ruff, pytest) and `.env` (copy `.env.example`; never committed).

The challenge data is not in the repository. `fetch_data.py` gets the public ITU and Traficom files and prints their SHA256. The frequencies-of-interest table is Traficom's synthetic dataset from the Since AI platform.

## Architecture

1. Ingest: IFIC `.mdb` → 15 CSV tables, register xlsx → CSV, M4 table JSON. Input hashes are logged.
2. Gates, all deterministic: G1 band overlap (space-to-Earth) → G2 visible from Finland (GSO elevation, non-GSO orbit reach) → G3 upper-bound PFD against RR Table 21-4 (`rules/rr21_table21_4.csv`) → G4 queue. Every drop has a reason code.
3. Case cards: JSON + Markdown, with source table and key for every number, M4 allocation and missing fields.
4. Outputs: `cases.json`, `cases.md`, `queue.md`, `funnel.json`, `3074_results.csv` (one row per notice), `run.log`.
5. Side quest: the same core with a terrestrial adapter, ITU-R P.1546-6 field strength, an issue-to-issue diff, and trends.

## Data, privacy and security

- ITU Space BR IFIC 3074 (public), Traficom open data table of frequency allocations (public), Traficom frequencies-of-interest table (synthetic, provided for the challenge), ITU Radio Regulations 2024.
- No personal data. The pipeline runs offline after the fetch.
- No secrets in the repo: configuration via `.env`.

## Technology inventory

| Item | Use | Licence |
|---|---|---|
| FastAPI | web API | MIT |
| openpyxl | register xlsx → CSV | MIT |
| mdbtools | IFIC `.mdb` → CSV | GPL / LGPL (system tool, not bundled) |
| _model_ | _card and letter prose_ | _..._ |

## AI tools used

- Claude Code: _what for_
- _..._

## Pre-existing work

This repository template (FastAPI skeleton, LLM client, test setup) was prepared before the event,
commit `6fe98b9`. The application code after that commit was built during the hackathon 6–8 Nov 2026.

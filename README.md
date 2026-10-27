# Project name

Since AI Hackathon 2026 · Challenge: _<company>_ · Team: Janne Rosama (solo)

## Problem

_What the challenge company needs, in 2–3 sentences._

## Solution

_What this does and why it helps. One screenshot or GIF._

## Demo

- Live: _<submission URL>_
- Video (~2 min): _<YouTube link>_

## Run it

```bash
cp .env.example .env      # set LLM_BASE_URL / LLM_API_KEY / LLM_MODEL
uv sync
uv run uvicorn app.main:app --reload
# http://localhost:8000
uv run pytest
```

## Architecture

_One diagram or 5 bullet points: data in -> processing -> model -> output._

## Data, privacy and security

- Data used and where it comes from (challenge rules apply).
- Where inference runs (local model / CSC Aitta / external API) and why.
- No secrets in the repo: configuration via `.env`.

## Technology inventory

| Item | Use | Licence |
|---|---|---|
| FastAPI | web API | MIT |
| _model_ | _..._ | _..._ |

## AI tools used

- Claude Code: _what for_
- _..._

## Pre-existing work

This repository template (FastAPI skeleton, LLM client, test setup) was prepared before the event,
commit `6fe98b9`. Everything after that commit was built during the hackathon 6–8 Nov 2026.

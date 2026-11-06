#!/bin/sh
# The whole demo in one command: fetch nothing, read data/, write out/.
# Prerequisites: uv sync, and data/ filled by scripts/fetch_data.py.
set -e
uv run python -m app.pipeline \
  --ific data/itu-ific-3074 \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json \
  --out out/
echo
echo "out/queue.md  - the cases a human decides (19 in the demo slice)"
echo "out/cases.md  - the full cards, with the audit trail"

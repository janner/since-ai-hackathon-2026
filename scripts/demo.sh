#!/bin/sh
# The whole demo in one command: fetch nothing, read data/, write out/.
# One run writes both the space funnel and the terrestrial side feature.
# Prerequisites: uv sync, and data/ filled by scripts/fetch_data.py.
set -e
uv run python -m app.pipeline \
  --ific data/itu-ific-3074/ific3074.mdb \
  --register data/frequencies_of_interest.csv \
  --m4 data/taajuusjakotaulukko.json \
  --terrestrial data/itu-terr-ific/brific3076.mdb \
  --terrestrial-prev data/itu-terr-ific/brific3075.mdb \
  --out out/
echo
queue_n=$(grep -m1 '^# Queue (' out/queue.md | tr -dc '0-9')
echo "out/queue.md  - the cases a human decides (${queue_n} in the demo slice)"
echo "out/cases.md  - the full cards, with the audit trail"
echo "out/TERRESTRIAL.md  - the terrestrial side feature, from the same run"

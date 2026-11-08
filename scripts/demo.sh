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
  --out out/ --all
echo
queue_n=$(sed -n 's/^## Needs attention (\([0-9]*\)).*/\1/p' out/queue.md)
queue_all=$(sed -n 's/^# Queue (\([0-9]*\) notices.*/\1/p' out/queue.md)
echo "out/queue.md  - every notice (${queue_all}), ${queue_n} need attention in the run"
echo "out/cases.md  - the full cards, with the audit trail"
echo "out/TERRESTRIAL.md  - the terrestrial side feature, from the same run"

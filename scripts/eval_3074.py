"""Score a 3074 run against the project's own labels (plan R16).

The labels are the project's reading, not Traficom ground truth (docs/decisions.md D15).
The output is an agreement count, never a recall or accuracy claim. See docs/eval-3074.md.

    python3 scripts/eval_3074.py [--run out/3074_results.csv] [--labels docs/eval-3074.csv]
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLASSES = ("exceeds", "near", "not_space", "clear", "cannot_decide")


def read_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        raise SystemExit(f"{path}: {exc}") from exc


def score(
    run_rows: list[dict[str, str]], label_rows: list[dict[str, str]]
) -> tuple[int, list[dict[str, str]]]:
    """Compare the run's class column with the own labels, one row per classified notice."""
    annotations: dict[str, dict[str, str]] = {}
    for row in label_rows:
        ntc_id = row.get("ntc_id", "").strip()
        label = row.get("label", "").strip()
        if label not in CLASSES:
            raise SystemExit(f"{ntc_id}: unknown label {label!r}")
        if ntc_id in annotations:
            raise SystemExit(f"duplicate label: {ntc_id}")
        annotations[ntc_id] = row

    classified = [row for row in run_rows if row.get("class", "").strip()]
    if not classified:
        raise SystemExit("the run has no classified rows")

    missing = [row["ntc_id"] for row in classified if row["ntc_id"] not in annotations]
    if missing:
        raise SystemExit("no label for: " + ", ".join(missing))
    stray = sorted(set(annotations) - {row["ntc_id"] for row in run_rows})
    if stray:
        raise SystemExit("label not in the run: " + ", ".join(stray))

    rows = [
        {
            **row,
            "label": annotations[row["ntc_id"]]["label"].strip(),
            "rationale": annotations[row["ntc_id"]].get("rationale", "").strip(),
        }
        for row in run_rows
        if row.get("class", "").strip()
    ]
    agreed = sum(1 for row in rows if row["class"] == row["label"])
    return agreed, rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eval_3074", description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT / "out" / "3074_results.csv")
    parser.add_argument("--labels", type=Path, default=ROOT / "docs" / "eval-3074.csv")
    args = parser.parse_args(argv)

    agreed, rows = score(read_rows(args.run), read_rows(args.labels))

    print(f"own labels: {agreed}/{len(rows)} agree ({100 * agreed / len(rows):.1f}%)")
    print("own labels only, not Traficom ground truth")

    run_counts = Counter(row["class"] for row in rows)
    own_counts = Counter(row["label"] for row in rows)
    print("\nclass counts:")
    print(f"  {'class':<13} run own")
    for klass in CLASSES:
        print(f"  {klass:<13} {run_counts[klass]:>3} {own_counts[klass]:>3}")

    differences = [row for row in rows if row["class"] != row["label"]]
    print(f"\ndifferences ({len(differences)}):")
    for row in differences:
        margin = row.get("margin_db") or "-"
        print(
            f"  {row['ntc_id']:<12} run={row['class']:<13} own={row['label']:<13} "
            f"margin={margin:>7}  {row['rationale']}"
        )
    if not differences:
        print("  none")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""CLI: run the funnel over one Space IFIC package and write the six output files.

    python -m app.pipeline --ific data/itu-ific-3074 --register data/frequencies_of_interest.csv \
        --m4 data/taajuusjakotaulukko.json --out out/

The run never touches the network. The LLM is optional: without LLM_BASE_URL every card
falls back to the deterministic template.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from app import cards as card_writer
from app import gates, ingest, pfd, prose
from app.bands import derive_bands, groups, select_bands, stations_on
from app.config import DEMO_SLICE_MHZ, RULES_VERSION

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LIMITS = REPO_ROOT / "rules" / "rr21_table21_4.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.pipeline",
        description="Determine the worst-case PFD of Space IFIC notices against Finnish stations.",
    )
    parser.add_argument("--ific", required=True, type=Path, help="IFIC package dir (holds csv/)")
    parser.add_argument("--register", required=True, type=Path, help="frequencies_of_interest.csv")
    parser.add_argument("--m4", required=True, type=Path, help="taajuusjakotaulukko.json")
    parser.add_argument("--out", type=Path, default=Path("out"), help="output directory")
    parser.add_argument("--limits", type=Path, default=DEFAULT_LIMITS, help="Table 21-4 CSV")
    parser.add_argument(
        "--all",
        action="store_true",
        help="screen all seven space bands instead of the 3,47-3,78 GHz demo slice",
    )
    return parser.parse_args(argv)


def run(
    ific_dir: Path,
    register: Path,
    m4: Path,
    out: Path = Path("out"),
    limits: Path = DEFAULT_LIMITS,
    all_bands: bool = False,
) -> int:
    started = time.monotonic()
    ific = ingest.load_ific(ific_dir)
    stations, _ = ingest.load_register(register)
    m4_rows = ingest.load_m4(m4)
    limits_rows = pfd.load_limits(limits)

    all_derived = derive_bands(stations)
    bands = all_derived if all_bands else select_bands(all_derived, *DEMO_SLICE_MHZ)
    if not bands:
        raise ingest.DataError(
            "no protected band derived from the register for this selection; "
            "check --register and the seven space bands in app/config.py"
        )
    on_band = stations_on(stations, bands)

    result = gates.run(ific, on_band, bands, limits_rows, mode="all" if all_bands else "slice")
    result.run_at = datetime.now(UTC).astimezone().isoformat(timespec="seconds")
    result.rules_version = RULES_VERSION
    result.freq_rows = ific.counts.get("freq", 0)
    result.elapsed_s = time.monotonic() - started

    audit = {
        "input_sha256": result.input_sha256,
        "rules_version": result.rules_version,
        "run_at": result.run_at,
    }
    built = []
    for case in result.cases:
        card = card_writer.build_card(case, ific, m4_rows, audit)
        card["prose"] = prose.draft_summary(card)
        built.append(card)
    card_writer.write_outputs(result, ific, built, ific.counts, out)

    counts = result.counts
    print(
        f"{counts['notices']} notices → G1 {counts['g1']} → G2 {counts['g2']} → "
        f"G3 {counts['g3']} + {counts['cannot_decide']} cannot decide"
    )
    print(
        f"exceeds {counts['exceeds']}, near {counts['near']}, clear {counts['clear']}, "
        f"{len(result.queue)} in the queue ({groups(bands)} groups, "
        f"{len(bands)} bands, {result.elapsed_s:.2f} s)"
    )
    print(f"wrote {out}/cases.json, cases.md, queue.md, funnel.json, 3074_results.csv, run.log")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(args.ific, args.register, args.m4, args.out, args.limits, args.all)
    except ingest.DataError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

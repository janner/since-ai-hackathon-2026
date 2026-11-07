"""CLI: run the funnel over one Space IFIC MDB and write the output files.

    python -m app.pipeline --ific data/itu-ific-3074/ific3074.mdb \
        --register data/frequencies_of_interest.csv \
        --m4 data/taajuusjakotaulukko.json --out out/

The tables are read straight from the BR IFIC Access database with `mdb-export`; there is no
intermediate CSV directory. Add `--terrestrial <3076.mdb> --terrestrial-prev <3075.mdb>` and
the same run also writes the terrestrial side feature into the same `--out` directory. Without
the flag the space run is exactly what it was.

The deterministic path never touches the network. The optional LLM prose step calls
`LLM_BASE_URL` when it is set; without it every card falls back to the template.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from app import cards as card_writer
from app import gates, ingest, pfd, prose, terrestrial
from app.bands import Band, groups
from app.config import DEMO_SLICE_MHZ, RULES_VERSION, SPACE_BANDS_MHZ
from app.territory import places as territory_places

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LIMITS = REPO_ROOT / "rules" / "rr21_table21_4.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.pipeline",
        description="Determine the worst-case PFD of Space IFIC notices against Finnish stations.",
    )
    parser.add_argument(
        "--ific",
        required=True,
        type=Path,
        help="Space BR IFIC Access database (e.g. data/itu-ific-3074/ific3074.mdb)",
    )
    parser.add_argument("--register", required=True, type=Path, help="frequencies_of_interest.csv")
    parser.add_argument("--m4", required=True, type=Path, help="taajuusjakotaulukko.json")
    parser.add_argument("--out", type=Path, default=Path("out"), help="output directory")
    parser.add_argument("--limits", type=Path, default=DEFAULT_LIMITS, help="Table 21-4 CSV")
    parser.add_argument(
        "--all",
        action="store_true",
        help="screen all seven space bands instead of the 3,47-3,78 GHz demo slice",
    )
    parser.add_argument(
        "--terrestrial",
        type=Path,
        default=None,
        help="also run the terrestrial side feature on this BR IFIC MDB (current issue)",
    )
    parser.add_argument(
        "--terrestrial-prev",
        type=Path,
        default=None,
        help="previous BR IFIC MDB for the trend baseline (default: --terrestrial)",
    )
    return parser.parse_args(argv)


def run(
    ific_mdb: Path,
    register: Path,
    m4: Path,
    out: Path = Path("out"),
    limits: Path = DEFAULT_LIMITS,
    all_bands: bool = False,
    terrestrial_path: Path | None = None,
    terrestrial_prev: Path | None = None,
) -> int:
    started = time.monotonic()
    ific = ingest.load_ific(ific_mdb)
    scope = SPACE_BANDS_MHZ if all_bands else (DEMO_SLICE_MHZ,)
    # Only the register rows on the run's bands can be a reference; the rest never reach a gate.
    stations, _ = ingest.load_register(register, scope)
    m4_rows = ingest.load_m4(m4)
    try:
        limits_rows = pfd.load_limits(limits)
    except (OSError, KeyError, ValueError) as error:
        raise ingest.DataError(f"cannot read limits {limits}: {error}") from error

    # The run's bands come from the scope, not from the register: the Excel list is a
    # reference, and the bands nobody listed are exactly the ones a satellite should not use.
    bands = [
        Band(lo_mhz=lo_mhz, hi_mhz=hi_mhz, group=index, stations=())
        for index, (lo_mhz, hi_mhz) in enumerate(scope)
    ]

    result = gates.run(
        ific,
        stations,
        list(territory_places()),
        bands,
        limits_rows,
        m4_rows,
        mode="all" if all_bands else "slice",
    )
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
        f"exceeds {counts['exceeds']}, near {counts['near']}, not_space {counts['not_space']}, "
        f"clear {counts['clear']}, {len(result.queue)} in the queue ({groups(bands)} groups, "
        f"{len(bands)} bands, {result.elapsed_s:.2f} s)"
    )
    results = f"{card_writer.ifact_tag(ific)}_results.csv"
    print(f"wrote {out}/cases.json, cases.md, queue.md, funnel.json, {results}, run.log, letters/")

    if terrestrial_path is not None:
        # Same command, same out/, same source/audit/missing contract; a separate
        # calculation path (P.1546-6 vs. the PFD gates). No previous MDB given means
        # the current one is also the trend baseline.
        prev = terrestrial_prev or terrestrial_path
        try:
            doc = terrestrial.run(
                terrestrial.load_issue_mdb(prev),
                terrestrial.load_issue_mdb(terrestrial_path),
                register,
                out,
            )
        except ValueError as error:
            raise ingest.DataError(str(error)) from error
        print(
            f"terrestrial {doc['issues']['prev']}→{doc['issues']['curr']}: "
            f"{doc['diff']['new']} new, {doc['diff']['modified']} modified, "
            f"{doc['diff']['withdrawn']} withdrawn, {len(doc['notices'])} notices in reach"
        )
        print(f"wrote {out}/terrestrial_findings.json, terrestrial_trends.csv, TERRESTRIAL.md")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(
            args.ific,
            args.register,
            args.m4,
            args.out,
            args.limits,
            args.all,
            args.terrestrial,
            args.terrestrial_prev,
        )
    except ingest.DataError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

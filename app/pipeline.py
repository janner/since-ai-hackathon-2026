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
from app import gates, ingest, ledger, pfd, prose, terrestrial
from app.allocation import finnish_bands
from app.bands import Band
from app.config import DEMO_SLICE_MHZ, RULES_VERSION
from app.territory import places as territory_places

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LIMITS = REPO_ROOT / "rules" / "rr21_table21_4.csv"
# The pseudonym the pipeline writes into the ledger's actor field; never a real name.
LEDGER_ACTOR = "spec-01"


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
        help="every Finnish allocation (the default; kept so older commands still run)",
    )
    parser.add_argument(
        "--slice",
        action="store_true",
        help="the 3,47-3,78 GHz demo slice, with G1's old narrow band screen (demo only)",
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
    parser.add_argument(
        "--ledger",
        action="store_true",
        help="also register every flagged case in the complaint ledger (ledger/complaints.jsonl)",
    )
    return parser.parse_args(argv)


def run(
    ific_mdb: Path,
    register: Path,
    m4: Path,
    out: Path = Path("out"),
    limits: Path = DEFAULT_LIMITS,
    slice_bands: bool = False,
    terrestrial_path: Path | None = None,
    terrestrial_prev: Path | None = None,
    ledger_events: bool = False,
) -> int:
    started = time.monotonic()
    ific = ingest.load_ific(ific_mdb)
    m4_rows = ingest.load_m4(m4)
    # The default covers every Finnish allocation and G1 screens every space-to-Earth row,
    # whatever its frequency: a band with no satellite service is exactly where a satellite
    # should not transmit (D18). The demo slice stays a flag and keeps G1's old narrow screen.
    scope = (DEMO_SLICE_MHZ,) if slice_bands else tuple(finnish_bands(m4_rows))
    # Only the register rows on the run's bands can be a reference; the rest never reach a gate.
    stations, _ = ingest.load_register(register, scope)
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

    # The run's own date is the reference for "a deadline is still upcoming"; the same instant
    # is the run_at stamp below.
    now = datetime.now(UTC).astimezone()
    result = gates.run(
        ific,
        stations,
        list(territory_places()),
        bands,
        limits_rows,
        m4_rows,
        mode="slice" if slice_bands else "all",
        today=now.date(),
        screen_bands=slice_bands,
    )
    result.run_at = now.isoformat(timespec="seconds")
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
        f"clear {counts['clear']}, {len(result.queue)} in the queue "
        f"({len(bands)} bands, {result.elapsed_s:.2f} s)"
    )
    results = f"{card_writer.ifact_tag(ific)}_results.csv"
    print(
        f"wrote {out}/cases.json, cases.md, queue.md, queue.json, funnel.json, {results}, "
        "run.log, letters/"
    )

    if ledger_events:
        registered = register_complaints(built, out)
        print(f"ledger: {registered} complaints registered in {ledger.ledger_dir()}")

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


def register_complaints(cards: list[dict], out: Path) -> int:
    """Open a complaint for every case the funnel flagged, and a letter for the `exceeds` ones.

    Idempotent: a case that already has an open complaint, or a network already under one, is
    skipped, so a re-run of the same IFIC adds no line. Only `opened` and `letter_sent` are written
    here; the outcome is a human decision (`POST /api/complaints/{id}/events`).
    """
    known = ledger.read()
    new: list[dict] = []
    for card in cards:
        issue_type = ledger.CLASS_ISSUES.get(card["class"])
        if issue_type is None:
            continue
        case_id = card["case_id"]
        same_network = tuple(card.get("same_network") or ())
        if ledger.open_complaint(known + new, case_id, same_network):
            continue
        at = ledger.now()
        new.append(
            ledger.event(
                case_id,
                "opened",
                at,
                LEDGER_ACTOR,
                {
                    "ific": int(card["source"]["ific"]),
                    "case_id": case_id,
                    "ntc_id": card["source"]["keys"]["ntc_id"],
                    "adm": card["parties"]["admin"],
                    "network_org": card["parties"]["network_org"],
                    "sat_name": card["coverage"]["sat_name"],
                    "band": card["band"],
                    "m4_services": (card.get("m4") or {}).get("services_in_finland"),
                    "class": card["class"],
                    "regulatory_stage": (card.get("regulatory_stage") or {}).get("provision"),
                    "issue_type": issue_type,
                    "source_sha256": card["audit"]["input_sha256"],
                    "rules_version": card["audit"]["rules_version"],
                    "same_network": list(same_network),
                },
            )
        )
        if card["class"] == "exceeds":
            new.append(
                ledger.event(
                    case_id,
                    "letter_sent",
                    at,
                    LEDGER_ACTOR,
                    {
                        "letter": str(out / "letters" / f"{case_id}.md"),
                        "action": "comment_sent",
                    },
                )
            )
    if new:
        ledger.append(new)
    return len({ev["complaint_id"] for ev in new})


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        return run(
            args.ific,
            args.register,
            args.m4,
            args.out,
            args.limits,
            args.slice,
            args.terrestrial,
            args.terrestrial_prev,
            args.ledger,
        )
    except ingest.DataError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

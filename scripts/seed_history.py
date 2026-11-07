"""Seed the demo complaint history: deterministic synthetic ledger rows, Jan 2021 - Oct 2026.

    python scripts/seed_history.py --seed 2026 [--out ledger]

One seed writes one file, byte for byte (`--out` defaults to `KAISTA_LEDGER` or `<repo>/ledger`).
Everything lands in `complaints.synthetic.jsonl` with `synthetic: true` on every line, never in the
real log: the demo history must never be readable as a record of real complaints. Administration
codes are real ITU codes, network names are invented (`SYN-` prefix) so the demo claims nothing
about a real operator. The last two weeks and IFIC 3074+ are left to the real runs (3075, 3076).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
# `python scripts/seed_history.py` puts scripts/ on sys.path, not the repo: the same command the
# docs give has to work, so the repo root goes on the path before app is imported.
sys.path.insert(0, str(REPO_ROOT))

from app import ledger  # noqa: E402
from app.config import SPACE_BANDS_MHZ  # noqa: E402

HELSINKI = ZoneInfo("Europe/Helsinki")
TABLE_21_4 = REPO_ROOT / "rules" / "rr21_table21_4.csv"

NEWEST_IFIC = 3073  # 3075 and 3076 are the real rows; the synthetic series stays below them
NEWEST_SLOT = date(2026, 10, 24)  # a fortnight before the demo; each earlier slot is 14 days back
SLOTS = 152  # two-week slots back to January 2021
SECOND_COMPLAINT_SHARE = 30  # per cent of slots carry a second notice
OPEN_SHARE = 30  # per cent still open (pending)

ADMINS = (
    ("RUS", 14),
    ("CHN", 13),
    ("USA", 13),
    ("GBR", 8),
    ("FRA", 8),
    ("DEU", 6),
    ("ITA", 5),
    ("IND", 5),
    ("BRA", 5),
    ("JPN", 5),
    ("LUX", 4),
    ("NLD", 4),
    ("NOR", 3),
    ("SWE", 3),
    ("EST", 2),
)
NETWORKS = (
    ("SYN-ORION", 14),
    ("SYN-VEGA", 13),
    ("SYN-ATLAS", 13),
    ("SYN-LYRRA", 8),
    ("SYN-NORD", 7),
    ("SYN-HELIOS", 6),
    ("SYN-CYGNUS", 5),
    ("SYN-AURIGA", 5),
    ("SYN-DRACO", 4),
    ("SYN-PAVO", 4),
    ("SYN-MIRA", 3),
    ("SYN-TUCANA", 3),
)
ISSUES = (
    ("pfd_exceedance", 40),
    ("near_limit", 25),
    ("band_without_satellite_allocation", 15),
    ("missing_data", 10),
    ("terrestrial_field_strength", 10),
)
OUTCOMES = (
    ("filing_modified", 20),
    ("coordination_agreement", 15),
    ("no_reply", 15),
    ("filing_withdrawn", 8),
    ("rejected_by_counterparty", 7),
    ("no_action_needed", 5),
)
# The band a complaint is about, weighted towards the demo slice.
BAND_WEIGHTS = (60, 8, 8, 6, 6, 6, 6)
ISSUE_CLASS = {
    "pfd_exceedance": "exceeds",
    "near_limit": "near",
    "band_without_satellite_allocation": "not_space",
    "missing_data": "cannot_decide",
    "terrestrial_field_strength": "exceeds",
}
# What the officer did after the letter, if anything was recorded at all.
ACTIONS = ("coordination_requested", "br_assistance_requested", "no_action_decided")
ACTION_SHARE = 35
PROVISIONS = ("No. 9.1", "No. 9.6", "No. 11.2", "Resolution 49")
M4_SERVICES = (
    "FIXED-SATELLITE; MOBILE-SATELLITE",
    "FIXED-SATELLITE",
    "BROADCASTING-SATELLITE; FIXED-SATELLITE",
    "MOBILE-SATELLITE",
    "FIXED-SATELLITE; EARTH-EXPLORATION-SATELLITE",
)


def bands(rng: random.Random) -> tuple[float, float]:
    """Kaista's own M4 bands plus the Table 21-4 ranges, with the demo slice most likely."""
    table = set(SPACE_BANDS_MHZ)
    if TABLE_21_4.is_file():
        with TABLE_21_4.open(newline="", encoding="utf-8") as handle:
            table.update(
                (float(row["freq_lo_mhz"]), float(row["freq_hi_mhz"]))
                for row in csv.DictReader(handle)
            )
    table = sorted(table)
    weights = list(BAND_WEIGHTS) + [4] * (len(table) - len(BAND_WEIGHTS))
    return rng.choices(table, weights=weights[: len(table)], k=1)[0]


def weighted(rng: random.Random, table: tuple[tuple[str, int], ...]) -> str:
    return rng.choices([key for key, _ in table], weights=[w for _, w in table], k=1)[0]


def stamp(day: date, rng: random.Random) -> str:
    return datetime(
        day.year, day.month, day.day, rng.randrange(8, 18), rng.randrange(0, 60), tzinfo=HELSINKI
    ).isoformat(timespec="seconds")


def build(seed: int) -> list[dict]:
    """The whole synthetic history for one seed: a complaint is a list of its events."""
    rng = random.Random(seed)
    events: list[dict] = []
    actor = "spec-01"
    for slot in range(SLOTS):
        day = NEWEST_SLOT - timedelta(days=14 * slot)
        ific = NEWEST_IFIC - slot
        for _ in range(1 + (rng.random() * 100 < SECOND_COMPLAINT_SHARE)):
            actor = f"spec-0{rng.randrange(1, 4)}"
            events.extend(complaint(rng, day, ific, actor))
    return events


def complaint(rng: random.Random, day: date, ific: int, actor: str) -> list[dict]:
    """One complaint: opened, maybe a letter, maybe a decision, then closed or left pending."""
    adm = weighted(rng, ADMINS)
    network = weighted(rng, NETWORKS)
    sat_name = f"{network}-{rng.choice((1, 2, 3))}"
    issue_type = weighted(rng, ISSUES)
    lo, hi = bands(rng)
    ntc_id = str(rng.randrange(100_000_000, 1_000_000_000))
    case_id = f"{ific}-{ntc_id}"
    opened_at = stamp(day, rng)
    out = [
        ledger.event(
            case_id,
            "opened",
            opened_at,
            actor,
            {
                "ific": ific,
                "case_id": case_id,
                "ntc_id": ntc_id,
                "adm": adm,
                "network_org": f"{network} SATCOM",
                "sat_name": sat_name,
                "band": {
                    "freq_min_mhz": lo,
                    "freq_max_mhz": hi,
                    "bandwidth_mhz": round(hi - lo, 2),
                },
                "m4_services": rng.choice(M4_SERVICES),
                "class": ISSUE_CLASS[issue_type],
                "regulatory_stage": rng.choice(PROVISIONS),
                "issue_type": issue_type,
                "source_sha256": "".join(rng.choice("0123456789abcdef") for _ in range(64)),
                "rules_version": "1.1.0",
                "same_network": [],
            },
            synthetic=True,
        )
    ]
    if issue_type == "missing_data":
        return out  # no data to write to the other administration about
    letter_at = datetime.fromisoformat(opened_at) + timedelta(days=rng.randrange(0, 6))
    out.append(
        ledger.event(
            case_id,
            "letter_sent",
            letter_at.isoformat(timespec="seconds"),
            actor,
            {"letter": f"letters/{case_id}.md", "action": "comment_sent"},
            synthetic=True,
        )
    )
    if rng.random() * 100 < ACTION_SHARE:
        decided = letter_at + timedelta(days=rng.randrange(1, 26))
        out.append(
            ledger.event(
                case_id,
                "action_recorded",
                decided.isoformat(timespec="seconds"),
                actor,
                {"action": rng.choice(ACTIONS), "note": "recorded for the demo history"},
                synthetic=True,
            )
        )
    if rng.random() * 100 < OPEN_SHARE:
        return out  # still open: no reply yet
    outcome = weighted(rng, OUTCOMES)
    if outcome == "no_reply":
        closed = letter_at + timedelta(days=90)
    else:
        # Days from the letter to the reply: a lognormal tail, which is what the register sees.
        reply_at = letter_at + timedelta(days=min(180, max(3, int(rng.lognormvariate(3.2, 0.8)))))
        out.append(
            ledger.event(
                case_id,
                "reply_received",
                reply_at.isoformat(timespec="seconds"),
                actor,
                {"outcome": outcome, "note": "reply from the other administration"},
                synthetic=True,
            )
        )
        closed = reply_at + timedelta(days=rng.randrange(0, 15))
    out.append(
        ledger.event(
            case_id,
            "closed",
            closed.isoformat(timespec="seconds"),
            actor,
            {"outcome": outcome},
            synthetic=True,
        )
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python scripts/seed_history.py", description=__doc__)
    parser.add_argument("--seed", type=int, default=2026, help="the RNG seed (2026 = the demo)")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="ledger directory (default: KAISTA_LEDGER or <repo>/ledger)",
    )
    args = parser.parse_args(argv)
    events = build(args.seed)
    path = ledger.write_all(events, directory=args.out)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"{len(ledger.complaints(events))} complaints, {len(events)} events -> {path}")
    print(f"sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

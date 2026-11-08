"""The M4 axis split at every overlapping row edge, with the downlink answer per piece.

The card asks one question per segment: does any row that covers the whole segment name a
space-to-Earth allocation? A row that only touches the segment edge does not cover it.
"""

from pathlib import Path

import pytest

from app.allocation import downlink_use, m4_lookup, segments
from app.config import M4_SERVICES, M4_SUB_HI, M4_SUB_LO
from app.ingest import load_m4

M4 = Path(__file__).resolve().parent.parent / "data" / "taajuusjakotaulukko.json"


def row(row_id: int, lo_mhz: float, hi_mhz: float, services: str) -> dict:
    return {
        "ID": row_id,
        M4_SUB_LO: lo_mhz * 1e6,
        M4_SUB_HI: hi_mhz * 1e6,
        M4_SERVICES: services,
    }


def test_overlapping_rows_split_the_axis_and_only_the_downlink_row_allows_downlink():
    rows = [
        row(1, 7933.0, 8157.0, "FIXED"),
        row(2, 8025.0, 8400.0, "EARTH EXPLORATION-SATELLITE (SPACE-TO-EARTH)"),
        row(3, 8243.0, 8467.0, "FIXED"),
    ]
    parts = segments(rows, 7900.0, 8500.0)
    assert [(part["lo_mhz"], part["hi_mhz"]) for part in parts] == [
        (7900.0, 7933.0),
        (7933.0, 8025.0),
        (8025.0, 8157.0),
        (8157.0, 8243.0),
        (8243.0, 8400.0),
        (8400.0, 8467.0),
        (8467.0, 8500.0),
    ]
    assert [part["downlink"] for part in parts] == [False, False, True, True, True, False, False]
    # A segment with no covering row at all is "not allocated", not "allocated, no downlink".
    assert parts[0]["services"] == []
    assert parts[1]["services"] == ["FIXED"]
    assert parts[2]["m4_row_ids"] == [1, 2]


def test_touching_an_edge_is_not_overlap():
    rows = [row(1, 7933.0, 8157.0, "FIXED")]
    ends_at_edge = segments(rows, 7800.0, 7933.0)
    assert [(part["lo_mhz"], part["hi_mhz"]) for part in ends_at_edge] == [(7800.0, 7933.0)]
    assert ends_at_edge[0]["services"] == []
    assert ends_at_edge[0]["downlink"] is False
    starts_at_edge = segments(rows, 7933.0, 8000.0)
    assert starts_at_edge[0]["services"] == ["FIXED"]


def test_band_with_no_m4_row_is_one_not_allocated_segment():
    lookup = m4_lookup([], 500_000.0, 500_100.0)
    assert lookup["services_in_finland"] == "not allocated"
    assert [(part["lo_mhz"], part["hi_mhz"], part["services"]) for part in lookup["segments"]] == [
        (500_000.0, 500_100.0, [])
    ]
    assert lookup["downlink_use"] is False
    assert lookup["downlink_gaps"] == [(500_000.0, 500_100.0)]
    parts = segments([], 500_000.0, 500_100.0)
    assert [
        (part["lo_mhz"], part["hi_mhz"], part["services"], part["downlink"]) for part in parts
    ] == [(500_000.0, 500_100.0, [], False)]


def test_uplink_only_row_is_a_satellite_service_but_not_a_downlink():
    rows = [row(1, 6000.0, 6010.0, "FIXED SATELLITE (EARTH-TO-SPACE)")]
    assert downlink_use("FIXED SATELLITE (EARTH-TO-SPACE)") is False
    part = segments(rows, 6000.0, 6010.0)[0]
    assert part["satellite"] is True  # D18: any direction is satellite use
    assert part["downlink"] is False  # but it is not an allocation of the downlink
    lookup = m4_lookup(rows, 6000.0, 6010.0)
    assert lookup["satellite_use"] is True
    assert lookup["downlink_gaps"] == [(6000.0, 6010.0)]


@pytest.mark.data
def test_the_8_ghz_rows_are_two_terrestrial_blocks_and_one_downlink_allocation():
    """7 933-8 157 and 8 243-8 467 are FIXED radiolinks, not satellite rows."""
    rows = load_m4(M4)
    by_id = {m4_row["ID"]: m4_row for m4_row in rows}
    assert [by_id[i][M4_SERVICES] for i in range(4349, 4354)] == ["FIXED"] * 5
    assert [by_id[i][M4_SERVICES] for i in range(4356, 4361)] == ["FIXED"] * 5
    assert [by_id[i][M4_SERVICES] for i in (4354, 4355)] == [
        "EARTH EXPLORATION-SATELLITE (SPACE-TO-EARTH)"
    ] * 2
    assert [by_id[i]["Direction"] for i in (4354, 4355)] == ["TX", "RX"]

    parts = segments(rows, 7900.0, 8500.0)
    assert [(part["lo_mhz"], part["hi_mhz"], part["downlink"]) for part in parts] == [
        (7900.0, 7933.0, False),
        (7933.0, 8025.0, False),
        (8025.0, 8157.0, True),
        (8157.0, 8243.0, True),
        (8243.0, 8400.0, True),
        (8400.0, 8467.0, False),
        (8467.0, 8500.0, False),
    ]
    # The downlink allocation is exactly 8 025-8 400 MHz, so a science beacon above it has none.
    juice = m4_lookup(rows, 8421.61975, 8450.479)
    assert juice["downlink_use"] is False
    assert juice["downlink_gaps"] == [(8421.62, 8450.479)]
    assert juice["segments"][0]["m4_row_ids"] == [4356, 4357, 4358, 4359, 4360]
    # Deterministic: the same input gives the same table.
    assert segments(rows, 7900.0, 8500.0) == parts

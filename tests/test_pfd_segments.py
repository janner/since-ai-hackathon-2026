"""The three Table 21-4 paths: a band crossing a row edge, several rows on one band, and a row
whose limit cannot be computed from IFIC data.

The fixtures are small hand-built tables so each path is proved without the real CSV's size;
the last two tests read the real rules file to prove the shipped table has the same shape.
"""

from pathlib import Path

import pytest

from app import gates, pfd
from app.gates import Case

RULES = Path(__file__).resolve().parent.parent / "rules" / "rr21_table21_4.csv"


def _row(lo, hi, orbit, a, k, ref, offset="", footnotes="", breakpoints=""):
    return pfd.LimitRow(
        freq_lo_mhz=lo,
        freq_hi_mhz=hi,
        orbit=orbit,
        a_db=a,
        k_db=k,
        ref_hz=ref,
        offset=offset,
        service="FSS (space-to-Earth)",
        page="p. 288",
        source="ITU RR 2024 Art. 21 Table 21-4",
        region="all",
        footnotes=footnotes,
        breakpoints=pfd._parse_breakpoints(breakpoints),
    )


# A 3 400-4 200 MHz GSO row and a 4 200-4 500 MHz any row: a band that ends at 4 202 crosses.
TWO_ROWS = [
    _row(3400, 4200, "GSO", -152, 10, 4000),
    _row(4200, 4500, "any", -152, 10, 4000),
]


def test_band_crossing_a_row_edge_is_split_and_a_part_with_no_row_is_a_gap():
    """Path 1: the band is computed part by part; the uncovered part is a fact, never clear."""
    segments = pfd.limit_segments(TWO_ROWS, 3998.0, 4202.0, "GSO")
    assert [(s.freq_lo_mhz, s.freq_hi_mhz) for s in segments] == [(3998.0, 4200.0), (4200.0, 4202.0)]
    assert segments[0].covered and segments[0].rows[0].freq_lo_mhz == 3400.0
    assert segments[1].covered and segments[1].rows[0].freq_lo_mhz == 4200.0

    # Outside both rows: the whole band is one gap and carries the fact.
    gap = pfd.limit_segments(TWO_ROWS, 4700.0, 4900.0, "GSO")
    assert [s.covered for s in gap] == [False]
    reason = pfd.no_agreed_limit_reason(gap[0].freq_lo_mhz, gap[0].freq_hi_mhz)
    assert reason.startswith("no_agreed_limit:")
    assert "4\u00a0700-4\u00a0900 MHz" in reason
    assert "no_limit_for_band" not in reason


def test_a_gap_keeps_a_clear_margin_out_of_the_clear_class():
    """A clear margin on the covered part must not read `clear` when another part has no row."""
    assert gates.classify(-5.0, band_satellite=True, no_agreed_limit=True) == "no_agreed_limit"
    assert gates.classify(-5.0, band_satellite=True) == "clear"
    # An exceedance stays the finding; the gap is a caveat on the same card.
    assert gates.classify(0.5, band_satellite=True, no_agreed_limit=True) == "exceeds"
    assert gates.classify(-1.0, band_satellite=True, no_agreed_limit=True) == "near"


def test_two_rows_on_the_same_band_report_the_worst_margin_and_name_the_row():
    """Path 2: 6 825-7 075 MHz has a 4 kHz and a 1 MHz limit; the tighter row must win."""
    rows = [
        _row(6825, 7075, "any", -154, 10, 4000),  # 4 kHz limit
        _row(6825, 7075, "any", -134, 10, 1000000),  # 1 MHz limit
    ]
    segments = pfd.limit_segments(rows, 6900.0, 7000.0, "GSO")
    assert len(segments) == 1
    assert len(segments[0].rows) == 2

    # At 5 deg the two limits differ: -154 - 10log10(4000) vs -134 - 10log10(1e6).
    four_khz = pfd.limit_hz(rows[0], 5.0)
    one_mhz = pfd.limit_hz(rows[1], 5.0)
    assert four_khz == pytest.approx(-190.02, abs=0.01)
    assert one_mhz == pytest.approx(-194.0, abs=0.01)
    # A level of -180 dB(W/m2/Hz) is 10.02 dB over the 4 kHz row and 14 dB over the 1 MHz row:
    # the 1 MHz row is the tighter one, and the worst margin belongs to it.
    worst = max(rows, key=lambda row: -180.0 - pfd.limit_hz(row, 5.0))
    assert worst is rows[1]
    assert round(-180.0 - pfd.limit_hz(worst, 5.0), 2) == 14.0
    # The card names the row and its footnote. 6 825-7 075 rows carry the "and" limits; the
    # footnote text names the 4 kHz/1 MHz split, so the citation must carry it too.
    assert "6\u00a0825-7\u00a0075 MHz" in rows[1].cite()
    assert "footnote" in _row(6700, 6825, "any", -137, 10, 4000, footnotes="17").cite()


def test_a_row_that_needs_a_footnote_formula_is_cannot_decide_named_by_the_footnote():
    """Path 3: footnote 18 (EESS active SAR) and 26 (NGSO ISS Res 679) are not a/k rows."""
    assert pfd.uncomputable_reason(_row(9900, 10400, "any", -113, 46.4, 4000, footnotes="18")) == (
        "footnote_18_eess_active"
    )
    assert pfd.uncomputable_reason(_row(27500, 30000, "NGSO", -120, 10, 4000, footnotes="26")) == (
        "footnote_26_ngso_iss"
    )
    # A computable row and an X row without N >= 1000 stay computable.
    assert pfd.uncomputable_reason(_row(10700, 11700, "GSO", -150, 10, 4000)) is None
    assert pfd.uncomputable_reason(_row(17700, 19300, "NGSO", -115, 10, 4000, "X", "7; 8; 13")) is None
    # The X offset without Nv names footnote 13.
    assert pfd.x_missing_reason(_row(17700, 19300, "NGSO", -115, 10, 4000, "X", "7; 8; 13")) == (
        "footnote_13_nv_missing"
    )
    assert "no_limit_for_band" not in "footnote_18_eess_active"
    assert "no_limit_for_band" not in "footnote_26_ngso_iss"


def test_breakpoints_are_piecewise_linear_and_continuous():
    """A non-standard row is read from its breakpoints, not from its a/k pair."""
    row = _row(
        37500,
        40000,
        "GSO",
        -127,
        22,
        4000,
        footnotes="21",
        breakpoints="0:-127;5:-127;20:-107;25:-105;90:-105",
    )
    # Flat 0-5 deg, linear 5-20, a short 20-25 slope and flat 25-90 deg. At 12.5 deg the value
    # is halfway between -127 and -107: -117 dB.
    assert pfd.limit_hz(row, 0.0) == pytest.approx(-127 - 10 * 3.60206, abs=0.01)
    assert pfd.limit_hz(row, 12.5) == pytest.approx(-117 - 10 * 3.60206, abs=0.01)
    assert pfd.limit_hz(row, 25.0) == pfd.limit_hz(row, 90.0)
    # Continuous at the kink: no jump between 19.999 and 20.001.
    assert abs(pfd.limit_hz(row, 19.999) - pfd.limit_hz(row, 20.001)) < 1e-2


def test_the_real_table_has_the_rows_the_three_paths_need():
    """The shipped CSV carries the footnote and breakpoint columns the code reads."""
    limits = pfd.load_limits(RULES)
    eess = next(row for row in limits if row.freq_lo_mhz == 9900.0 and row.orbit == "any")
    assert pfd.uncomputable_reason(eess) == "footnote_18_eess_active"
    assert eess.breakpoints and eess.breakpoints[0][0] == 0.0
    iss = next(row for row in limits if row.freq_lo_mhz == 27500.0 and row.orbit == "NGSO")
    assert pfd.uncomputable_reason(iss) == "footnote_26_ngso_iss"
    x_row = next(row for row in limits if row.freq_lo_mhz == 17700.0 and row.orbit == "NGSO")
    assert pfd.x_missing_reason(x_row) == "footnote_13_nv_missing"
    # A band that crosses the 4 200 MHz edge is split, not refused whole.
    segments = pfd.limit_segments(limits, 3998.0, 4202.0, "GSO")
    assert [s.covered for s in segments] == [True, False]

"""Geometry and the Table 21-4 limit: the two golden vectors and the edge cases."""

from pathlib import Path

import pytest

from app import pfd
from app.ingest import Orbit

RULES = Path(__file__).resolve().parent.parent / "rules" / "rr21_table21_4.csv"


@pytest.fixture(scope="module")
def limits() -> list[pfd.LimitRow]:
    return pfd.load_limits(RULES)


@pytest.fixture(scope="module")
def gso_row(limits) -> pfd.LimitRow:
    row = pfd.limit_row(limits, 3662.0, 3698.0, "GSO")
    assert row is not None
    return row


def test_table_has_thirteen_rows(limits):
    assert len(limits) == 13
    assert {row.orbit for row in limits} == {"GSO", "NGSO", "HEO", "any"}


def test_limit_row_needs_a_row_that_contains_the_whole_band(limits):
    assert pfd.limit_row(limits, 100.0, 200.0, "GSO") is None  # no_limit_for_band
    assert pfd.limit_row(limits, 3400.0, 4200.0, "GSO").freq_lo_mhz == 3400.0
    # 3 998 - 4 202 MHz sticks out of the 3 400-4 200 MHz row
    assert pfd.limit_row(limits, 3998.0, 4202.0, "GSO") is None


def test_heo_uses_the_ngso_row_when_there_is_no_heo_row(limits):
    row = pfd.limit_row(limits, 17800.0, 18000.0, "HEO")
    assert row.orbit == "NGSO"  # 17,7-19,3 GHz has no HEO row, so footnote 13 applies
    heo_band = pfd.limit_row(limits, 11000.0, 11200.0, "HEO")
    assert heo_band.orbit == "HEO"  # here the footnote 24 row exists


def test_vector_1_arithmetic(gso_row):
    """The plan's GSO vector: case 103500417, station 983816, 4,85 deg, 41 143 km."""
    elevation, distance = pfd.look(65.6981, 24.6245, 80.0)
    assert elevation == pytest.approx(4.85, abs=0.01)
    assert distance == pytest.approx(41143, abs=1)
    assert pfd.fspl(distance) == pytest.approx(163.28, abs=0.01)
    level = -50.0 + 28.5 - pfd.fspl(distance)
    assert level == pytest.approx(-184.78, abs=0.01)
    assert pfd.limit_hz(gso_row, elevation) == pytest.approx(-188.02, abs=0.01)
    assert level - pfd.limit_hz(gso_row, elevation) == pytest.approx(3.24, abs=0.01)


def test_vector_2_arithmetic():
    """The plan's non-GSO vector: perigee 592 km, worst angle 5,0 deg, 2 310 km."""
    row = pfd.load_limits(RULES)[1]  # 3 400-4 200 MHz NGSO, footnote 22/23
    assert row.a_db == -138.0 and row.offset == "Y"
    distance = pfd.slant(592.0, 5.0)
    assert distance == pytest.approx(2310, abs=2)
    level = -42.8 + 43.5 - pfd.fspl(distance)
    assert level == pytest.approx(-137.56, abs=0.05)
    assert pfd.limit_hz(row, 5.0) == pytest.approx(-198.0, abs=0.01)
    assert level - pfd.limit_hz(row, 5.0) == pytest.approx(60.44, abs=0.05)


def test_every_limit_row_is_continuous_at_25_degrees(limits):
    for row in limits:
        below = pfd.limit_hz(row, 25.0, 3.0)
        above = pfd.limit_hz(row, 25.0001, 3.0)
        assert abs(below - above) < 1e-3, row


def test_limit_hz_segments(gso_row):
    assert pfd.limit_hz(gso_row, 0.0) == pytest.approx(-188.02, abs=0.01)
    assert pfd.limit_hz(gso_row, 5.0) == pytest.approx(-188.02, abs=0.01)
    assert pfd.limit_hz(gso_row, 15.0) == pytest.approx(-183.02, abs=0.01)
    assert pfd.limit_hz(gso_row, 25.0) == pytest.approx(-178.02, abs=0.01)
    assert pfd.limit_hz(gso_row, 90.0) == pytest.approx(-178.02, abs=0.01)


def test_limit_hz_offset_applies_to_the_low_angles(gso_row):
    assert pfd.limit_hz(gso_row, 0.0, 5.0) == pytest.approx(-193.02, abs=0.01)
    assert pfd.limit_hz(gso_row, 25.0, 5.0) == pytest.approx(-178.02, abs=0.01)


def test_x_and_y_offsets():
    assert pfd.x_fn(50) == 0.0
    assert pfd.x_fn(288) == pytest.approx(10.0)
    assert pfd.x_fn(999) == pytest.approx(1401 / 69)
    assert pfd.x_fn(1000) is None  # N >= 1000 would need Nv, which IFIC does not give
    assert pfd.y_fn(1) == 0.0
    assert pfd.y_fn(2) == 0.0
    assert pfd.y_fn(100) == pytest.approx(10.0)


def test_ngso_reach():
    assert pfd.ngso_reach(_orbit(0.0, 650.0)) < 25  # equatorial LEO never shows in Finland
    assert pfd.ngso_reach(_orbit(97.8, 600.0)) > 60  # sun-synchronous orbit does
    assert pfd.ngso_reach(_orbit(None, None)) == 90.0  # no orbit data: never dropped at G2


def test_is_heo_needs_both_apogee_and_inclination():
    assert pfd.is_heo([_orbit(63.4, 40000.0)])
    assert not pfd.is_heo([_orbit(63.4, 15000.0)])
    assert not pfd.is_heo([_orbit(10.0, 40000.0)])


def test_look_returns_negative_elevation_below_the_horizon():
    elevation, _ = pfd.look(65.6981, 24.6245, -140.0)
    assert elevation < 0


def _orbit(inclination, apogee) -> Orbit:
    return Orbit(ntc_id="1", apog_km=apogee, perig_km=apogee, inclin_ang=inclination)

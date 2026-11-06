"""Gates G1-G4: the funnel counts, the drop reasons and the queue rules."""

import pytest

from app import gates


def test_class_boundaries():
    assert gates.classify(0.01) == "exceeds"
    assert gates.classify(0.0) == "near"  # a margin of exactly 0 is not an exceedance
    assert gates.classify(-3.0) == "clear"
    assert gates.classify(-2.99) == "near"


def test_mini_funnel_counts_and_reasons(mini):
    result = mini.result
    assert result.counts == {
        "notices": 9,
        "g1": 6,
        "g2": 4,
        "g3": 2,
        "cannot_decide": 2,
        "exceeds": 2,
        "near": 0,
        "clear": 0,
    }
    assert result.dropped == {
        "900000005": ("G1", "earth_station_notice"),
        "900000006": ("G1", "no_band_overlap"),
        "900000009": ("G1", "no_band_overlap"),  # sits in the hole: not protected
        "900000007": ("G2", "ngso_never_visible"),
        "900000008": ("G2", "geo_below_horizon"),
    }
    assert result.undecided == {"900000003": "no_orbit", "900000004": "no_power"}


def test_mini_vector_1_is_reproduced(mini):
    case = mini.result.case_by_id()["900000001"]
    assert case.orbit == "GSO"
    assert case.beam == "CDN"
    assert (case.victim.id, case.victim.licence) == ("900100001", "MVV")
    assert case.elev_deg == pytest.approx(4.85, abs=0.01)
    assert case.slant_km == pytest.approx(41143, abs=1)
    assert case.psd_dbw_hz == -50.0
    assert case.beam_gain_db == 28.5
    assert case.pfd_dbw_m2_hz == pytest.approx(-184.78, abs=0.01)
    assert case.limit_dbw_m2_hz == pytest.approx(-188.02, abs=0.01)
    assert case.margin_db == pytest.approx(3.24, abs=0.01)
    assert case.klass == "exceeds"


def test_mini_non_gso_case_uses_the_pass_sweep(mini):
    case = mini.result.case_by_id()["900000002"]
    assert case.orbit == "NGSO"
    assert case.perigee_km == 600.0
    assert case.elev_deg == 5.0  # the worst angle of the sampled pass
    assert case.slant_km == pytest.approx(2329, abs=1)
    assert case.margin_db == pytest.approx(58.16, abs=0.01)
    assert case.limit.service.startswith("FSS")


def test_queue_order_and_coverage_gap(mini):
    queue = mini.result.queue
    assert [item.klass for item in queue] == [
        "exceeds",
        "exceeds",
        "cannot_decide",
        "cannot_decide",
    ]
    assert [item.ntc_id for item in queue[:2]] == ["900000002", "900000001"]  # margin descending
    assert [item.reason for item in queue[2:]] == ["no_orbit", "no_power"]
    assert mini.result.coverage_gap == 16  # 20 seats, 4 items
    assert mini.result.overflow == {}


def test_gate4_overflows_in_class_order(mini):
    queue, overflow, gap = gates.gate4(mini.result.cases, mini.result.undecided, cap=1)
    assert len(queue) == 1
    assert queue[0].ntc_id == "900000002"
    assert overflow == {"exceeds": 1, "cannot_decide": 2}
    assert gap == 0


@pytest.mark.data
def test_demo_slice_funnel(challenge):
    result = challenge.slice.result
    assert result.counts == {
        "notices": 196,
        "g1": 41,
        "g2": 19,
        "g3": 18,
        "cannot_decide": 1,
        "exceeds": 9,
        "near": 5,
        "clear": 4,
    }
    assert result.reason_counts("G1") == {"no_band_overlap": 155}
    assert result.reason_counts("G2") == {"geo_below_horizon": 21, "ngso_never_visible": 1}
    assert result.undecided == {"126590032": "no_power"}
    assert (result.geo_visible, result.ngso_visible) == (16, 3)
    assert len(result.queue) == 19
    assert result.coverage_gap == 1
    assert result.overflow == {}
    assert len(result.cases) == 18
    assert len(result.stations) == 7


@pytest.mark.data
def test_all_bands_funnel(challenge):
    """All seven bands.

    The plan's counts for this mode (100 / 74 / 10) come from the reference tool reading the
    register's 25,2 GHz row "0,1G" as 0,1 MHz instead of the 0,1 GHz in its own
    "Channel bandwidth" column. Parsed as the register intends, one more notice overlaps:
    126545075, which cannot be decided because it has no orbit row. Everything else matches
    the plan: 64 computed cases, 26 / 15 / 23 and the queue of 20 with its overflow.
    """
    result = challenge.all.result
    assert result.counts == {
        "notices": 196,
        "g1": 101,
        "g2": 75,
        "g3": 64,
        "cannot_decide": 11,
        "exceeds": 26,
        "near": 15,
        "clear": 23,
    }
    assert result.drops == {
        "no_band_overlap": 94,
        "earth_station_notice": 1,
        "geo_below_horizon": 25,
        "ngso_never_visible": 1,
    }
    assert sorted(result.undecided) == [
        "124520174",
        "124520203",
        "125545392",
        "126545072",
        "126545073",
        "126545074",
        "126545075",
        "126545076",
        "126590032",
        "324520174",
        "324520203",
    ]
    assert len(result.queue) == 20
    assert result.overflow == {"exceeds": 6, "near": 15, "cannot_decide": 11, "clear": 23}
    assert result.coverage_gap == 0


@pytest.mark.data
def test_vector_2_from_the_real_data(challenge):
    """Case 124545403 (CHN, CSN-SSO): the plan's non-GSO vector.

    The table in the plan says perigee 600 km; the orbit row in IFIC 3074 says 592 km, and
    the slant range and every level below follow the 592 km the data carries.
    """
    case = challenge.slice.result.case_by_id()["124545403"]
    assert case.orbit == "NGSO"
    assert case.perigee_km == 592.0
    assert case.victim.id == "989011"
    assert case.psd_dbw_hz == -42.8
    assert case.beam_gain_db == 43.5
    assert case.elev_deg == pytest.approx(5.0, abs=0.1)
    assert case.slant_km == pytest.approx(2310, abs=2)
    assert case.fspl_db == pytest.approx(138.26, abs=0.01)
    assert case.pfd_dbw_m2_hz == pytest.approx(-137.56, abs=0.05)
    assert case.limit_dbw_m2_hz == pytest.approx(-198.0, abs=0.01)
    assert case.margin_db == pytest.approx(60.44, abs=0.05)
    assert case.klass == "exceeds"


@pytest.mark.data
def test_case_126590032_cannot_be_decided(challenge):
    result = challenge.slice.result
    assert result.undecided["126590032"] == "no_power"
    assert "126590032" in [item.ntc_id for item in result.queue]

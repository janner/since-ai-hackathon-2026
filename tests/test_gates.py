"""Gates G1-G4: the funnel counts, the drop reasons and the queue rules."""

from collections import Counter
from dataclasses import replace
from datetime import date

import pytest

from app import gates
from app.bands import Band
from app.config import NEAR_DB
from app.ingest import Freq, IficData, Notice


def _notice(ntc_id: str, ntc_type: str = "N") -> Notice:
    return Notice(ntc_id, "TST", ntc_type, "A", "11.2", "", "", "")


def _ific(freqs: list[Freq], notices: dict[str, Notice]) -> IficData:
    """A minimal IficData: gate1 only reads `freqs` and `notices`."""
    return IficData(
        notices=notices,
        freqs=freqs,
        beams={},
        emiss={},
        geo={},
        nongeo={},
        orbits={},
        links={},
        counts={},
        file="x.mdb",
        input_sha256="0" * 64,
    )


def test_class_boundaries():
    assert gates.classify(0.01) == "exceeds"
    assert gates.classify(0.0) == "near"  # a margin of exactly 0 is not an exceedance
    assert gates.classify(-3.0) == "clear"
    assert gates.classify(-2.99) == "near"


def test_guard_mhz_zero_is_the_plain_overlap(monkeypatch):
    from app import config

    freqs = [Freq("1", "B", "1", "E", 3600.0, 3610.0), Freq("2", "B", "2", "E", 3400.0, 3430.0)]
    notices = {"1": _notice("1"), "2": _notice("2")}
    band = Band(lo_mhz=3470.0, hi_mhz=3780.0, group=0, stations=("s1",))

    monkeypatch.setattr(config, "GUARD_MHZ", 0.0)
    found, dropped, adjacent = gates.gate1(_ific(freqs, notices), [band])
    assert set(found) == {"1"}  # 3 400-3 430 MHz does not overlap the band
    assert adjacent == set()
    assert dropped == {"2": ("G1", "no_band_overlap")}


def test_guard_mhz_lets_an_adjacent_notice_through(monkeypatch):
    """A notice inside the guard but outside the band enters and is marked adjacent."""
    from app import config

    freqs = [Freq("1", "B", "1", "E", 3600.0, 3610.0), Freq("2", "B", "2", "E", 3400.0, 3430.0)]
    notices = {"1": _notice("1"), "2": _notice("2")}
    band = Band(lo_mhz=3470.0, hi_mhz=3780.0, group=0, stations=("s1",))

    monkeypatch.setattr(config, "GUARD_MHZ", 50.0)
    found, dropped, adjacent = gates.gate1(_ific(freqs, notices), [band])
    assert set(found) == {"1", "2"}
    assert adjacent == {"2"}  # only the guard let it in
    assert "2" not in dropped


def test_a_notice_type_s_sending_E_is_dropped(monkeypatch):
    """An earth station notice sending "E" is the station transmitting, not a downlink."""
    from app import config

    freqs = [Freq("1", "B", "1", "E", 3600.0, 3610.0)]
    notices = {"1": _notice("1", ntc_type="S")}
    band = Band(lo_mhz=3470.0, hi_mhz=3780.0, group=0, stations=("s1",))
    monkeypatch.setattr(config, "GUARD_MHZ", 0.0)
    found, dropped, _ = gates.gate1(_ific(freqs, notices), [band])
    assert found == {}
    assert dropped == {"1": ("G1", "earth_station_notice")}


def test_notice_deadlines_pick_the_earliest_upcoming():
    """A notice has many groups; the deadline that matters is its earliest one still upcoming,
    falling back on the latest passed one when nothing is upcoming."""
    freqs = [
        Freq("1", "B", "g1", "E", 3600.0, 3610.0),
        Freq("1", "B", "g2", "E", 3600.0, 3610.0),
        Freq("2", "B", "g3", "E", 3600.0, 3610.0),
        Freq("3", "B", "g4", "E", 3600.0, 3610.0),  # this group carries no deadline
    ]
    notices = {"1": _notice("1"), "2": _notice("2"), "3": _notice("3")}
    ific = replace(
        _ific(freqs, notices),
        res35={"g1": date(2031, 1, 19), "g2": date(2026, 12, 19), "g3": date(2018, 1, 1)},
    )
    assert gates.notice_deadlines(ific, date(2026, 11, 7)) == {
        "1": (date(2026, 12, 19), False),
        "2": (date(2018, 1, 1), True),
    }


def test_queue_orders_by_stage_then_class_then_deadline():
    """The stage first, then the class, then the soonest upcoming deadline. The margin does
    not order. A passed deadline is behind every upcoming one; a notice with no deadline comes
    last."""
    notices = {str(i): _notice(str(i)) for i in range(1, 5)}  # all 11.2, one stage rank
    deadlines = {
        "1": (date(2031, 1, 19), False),
        "2": (date(2026, 12, 19), False),
        "3": (date(2019, 12, 18), True),
    }  # notice 4 has no deadline
    undecided = {ntc_id: "no_power" for ntc_id in notices}
    queue = gates.gate4([], undecided, notices, deadlines=deadlines)
    assert [item.ntc_id for item in queue] == ["2", "1", "3", "4"]


@pytest.mark.data
def test_demo_slice_funnel(challenge):
    result = challenge.slice.result
    assert result.counts == {
        "notices": 196,
        "g1": 41,
        "g2": 21,
        "g3": 20,
        "cannot_decide": 1,
        "exceeds": 11,
        "near": 5,
        "not_space": 4,
        "clear": 0,
    }
    assert result.reason_counts("G1") == {"no_band_overlap": 155}
    assert result.reason_counts("G2") == {"geo_below_horizon": 19, "ngso_never_visible": 1}
    assert result.undecided == {"126590032": "no_power"}
    # sensitivity: with the unknown PSD at 0 the margin is -required, so no grid search is needed
    field, required = result.required["126590032"]
    assert field == "psd"
    row = {item.ntc_id: item for item in result.queue}["126590032"]
    assert (row.unknown_field, row.required_db) == ("psd", required)
    assert "MOBILE AND FIXED" in row.band_use  # the band is on the row even without a card
    assert (result.geo_visible, result.ngso_visible) == (18, 3)
    # Every notice has a row: 21 need attention, the other 175 say why they do not.
    assert len(result.queue) == 196
    assert dict(Counter(item.tier for item in result.queue)) == {
        "attention": 21,
        "no_effect": 175,
    }
    assert len(result.cases) == 20
    assert len(result.places) == 552  # the territory edge, not the register's 871 rows


@pytest.mark.data
def test_all_bands_funnel(challenge):
    """Every Finnish allocation, with the territory edge as the PFD anchor.

    G1 passes every notice that has a space-to-Earth row in any Finnish allocation, whether or
    not the register lists a station there and whether or not the allocation is a satellite one:
    that is the point of the customer rule that the Excel list is only a reference and a band
    without satellite use is a finding. The register still supplies the reference row.
    """
    result = challenge.all.result
    # 124520203/324520203 (EESS active, footnote 18) are no longer read as an exceedance:
    # the row's limit is the SAR formula in the footnote, not its a/k pair, so the notice is
    # cannot_decide. The other rows' margins are unchanged except where the worst over several
    # rows is now reported (e.g. 124520174 37.9 -> 11.71 dB, still exceeds).
    assert result.counts == {
        "notices": 196,
        "g1": 176,
        "g2": 138,
        "g3": 102,
        "cannot_decide": 36,
        "exceeds": 54,
        "near": 30,
        "not_space": 2,
        "clear": 16,
    }
    assert result.drops == {
        "no_band_overlap": 12,
        "earth_station_notice": 8,
        "geo_below_horizon": 35,
        "ngso_never_visible": 3,
    }
    assert len(result.queue) == 196
    assert dict(Counter(item.tier for item in result.queue)) == {
        "attention": 122,
        "checked": 16,
        "no_effect": 58,
    }


@pytest.mark.data
def test_missing_perigee_cannot_be_decided(challenge):
    """A non-GSO notice whose orbit rows carry no perigee is a cannot_decide, not a clear."""
    ntc_id = "124545403"
    orbits = [replace(orbit, perig_km=None) for orbit in challenge.slice.ific.orbits[ntc_id]]
    ific = replace(challenge.slice.ific, orbits={**challenge.slice.ific.orbits, ntc_id: orbits})
    found, _, _ = gates.gate1(ific, challenge.slice.bands)
    cases, undecided, _ = gates.gate3(
        ific,
        {ntc_id: found[ntc_id]},
        challenge.slice.stations,
        challenge.slice.result.places,
        challenge.slice.limits,
        challenge.slice.m4,
    )
    assert cases == []
    assert undecided == {ntc_id: "no_perigee"}


@pytest.mark.data
def test_an_adjacent_case_is_capped_at_near(challenge):
    """A guard-only case keeps its computed margin but never reads as `exceeds`."""
    ntc_id = "103500417"  # margin +3,24 dB: exceeds on its own
    freqs = {
        ntc_id: [f for f in challenge.slice.ific.freqs if f.ntc_id == ntc_id and f.emi_rcp == "E"]
    }
    cases, _, _ = gates.gate3(
        challenge.slice.ific,
        freqs,
        challenge.slice.stations,
        challenge.slice.result.places,
        challenge.slice.limits,
        challenge.slice.m4,
        {ntc_id},
    )
    case = {c.ntc_id: c for c in cases}[ntc_id]
    assert case.adjacent is True
    assert case.margin_db == pytest.approx(3.25, abs=0.01)
    assert case.klass == "near"


@pytest.mark.data
def test_queue_holds_every_notice(challenge):
    """Nothing is invisible: every notice in the package has a queue row with a tier."""
    result = challenge.slice.result
    queued = {item.ntc_id for item in result.queue}
    assert queued == {c.ntc_id for c in result.cases} | set(result.undecided) | set(result.dropped)
    attention = {item.ntc_id for item in result.queue if item.tier == "attention"}
    assert attention == {c.ntc_id for c in result.cases if c.klass != "clear"} | set(
        result.undecided
    )
    checked = {item.ntc_id for item in result.queue if item.tier == "checked"}
    assert checked == {c.ntc_id for c in result.cases if c.klass == "clear"}
    no_effect = {item.ntc_id for item in result.queue if item.tier == "no_effect"}
    assert no_effect == set(result.dropped)


@pytest.mark.data
def test_a_clear_margin_on_a_non_satellite_band_is_still_a_finding(challenge):
    """The customer rule: PFD below the limit does not clear a band Finland does not use
    for satellite downlinks. Such a case is queued as `not_space`, not hidden as clear."""
    result = challenge.slice.result
    not_space = [case for case in result.cases if case.klass == "not_space"]
    assert not_space, "the demo band 3 470-3 780 MHz is not a satellite allocation in Finland"
    for case in not_space:
        assert case.band_satellite is False
        assert case.margin_db <= NEAR_DB
        assert case.ntc_id in {item.ntc_id for item in result.queue}
    # a clear case on a band Finland does allocate to a downlink stays in the queue as checked
    clear = [case for case in result.cases if case.klass == "clear"]
    tiers = {item.ntc_id: item.tier for item in result.queue}
    for case in clear:
        assert case.band_satellite is True
        assert tiers[case.ntc_id] == "checked"


@pytest.mark.data
def test_queue_order(challenge):
    """Stage first, then class, then the deadline; the margin does not order (Traficom, S1)."""
    queue = [item for item in challenge.slice.result.queue if item.tier == "attention"]
    assert {item.klass for item in queue} == {"exceeds", "near", "not_space", "cannot_decide"}
    keys = [gates.queue_key(item) for item in queue]
    assert keys == sorted(keys)
    stage_ranks = [item.stage_rank for item in queue]
    assert stage_ranks == sorted(stage_ranks)
    for stage_rank in {item.stage_rank for item in queue}:
        ranks = [
            gates.CLASS_ORDER.index(item.klass) for item in queue if item.stage_rank == stage_rank
        ]
        assert ranks == sorted(ranks)
    assert [item.reason for item in queue if item.klass == "cannot_decide"] == ["no_power"]


@pytest.mark.data
def test_only_one_demo_case_carries_a_res35_deadline(challenge):
    """One of the 20 demo cases falls in a group with a Resolution 35 deadline: 125500277, whose
    earliest upcoming group deadline is 19 Dec 2026 (the fixture's run date is 7 Nov 2026)."""
    result = challenge.slice.result
    with_deadline = {case.ntc_id: case for case in result.cases if case.deadline}
    assert set(with_deadline) == {"125500277"}
    assert with_deadline["125500277"].deadline == date(2026, 12, 19)
    assert with_deadline["125500277"].deadline_passed is False
    # it sorts ahead of a larger margin in the same class and stage: its group falls due
    first = next(i for i, item in enumerate(result.queue) if item.ntc_id == "125500277")
    bigger = next(i for i, item in enumerate(result.queue) if item.ntc_id == "125500066")
    assert result.queue[first].stage_rank == result.queue[bigger].stage_rank
    assert first < bigger


@pytest.mark.data
def test_queue_puts_coordination_before_notification(challenge):
    """The stage another administration can still influence comes before a recorded filing."""
    queue = [item for item in challenge.slice.result.queue if item.tier == "attention"]
    assert queue[0].stage_rank == 0  # advance publication or coordination request
    ranks = [item.stage_rank for item in queue]
    assert ranks == sorted(ranks)


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

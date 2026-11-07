"""Gates G1-G4: the funnel counts, the drop reasons and the queue rules."""

from dataclasses import replace

import pytest

from app import gates
from app.bands import Band
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
    # sensitivity: with the unknown PSD at 0 the margin is -required, so no grid search is needed
    field, required = result.required["126590032"]
    assert field == "psd"
    row = {item.ntc_id: item for item in result.queue}["126590032"]
    assert (row.unknown_field, row.required_db) == ("psd", required)
    assert (result.geo_visible, result.ngso_visible) == (16, 3)
    assert len(result.queue) == 15  # 9 exceeds + 5 near + 1 cannot_decide; the 4 clear stay out
    assert len(result.cases) == 18
    assert len(result.stations) == 7


@pytest.mark.data
def test_all_bands_funnel(challenge):
    """All seven bands.

    The plan's counts for this mode (100 / 74 / 10) come from the reference tool reading the
    register's 25,2 GHz row "0,1G" as 0,1 MHz instead of the 0,1 GHz in its own
    "Channel bandwidth" column. Parsed as the register intends, one more notice overlaps:
    126545075, which cannot be decided because it has no orbit row. Everything else matches
    the plan: 64 computed cases, 26 / 15 / 23 and the queue of 52.
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
    assert len(result.queue) == 52  # 26 exceeds + 15 near + 11 cannot_decide; 23 clear stay out


@pytest.mark.data
def test_missing_perigee_cannot_be_decided(challenge):
    """A non-GSO notice whose orbit rows carry no perigee is a cannot_decide, not a clear."""
    ntc_id = "124545403"
    orbits = [replace(orbit, perig_km=None) for orbit in challenge.slice.ific.orbits[ntc_id]]
    ific = replace(challenge.slice.ific, orbits={**challenge.slice.ific.orbits, ntc_id: orbits})
    found, _, _ = gates.gate1(ific, challenge.slice.bands)
    cases, undecided, _ = gates.gate3(
        ific, {ntc_id: found[ntc_id]}, challenge.slice.result.stations, challenge.slice.limits
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
        challenge.slice.result.stations,
        challenge.slice.limits,
        {ntc_id},
    )
    case = {c.ntc_id: c for c in cases}[ntc_id]
    assert case.adjacent is True
    assert case.margin_db == pytest.approx(3.24, abs=0.01)
    assert case.klass == "near"


@pytest.mark.data
def test_queue_holds_every_concern_and_no_clear(challenge):
    result = challenge.slice.result
    queued = {item.ntc_id for item in result.queue}
    assert queued == {c.ntc_id for c in result.cases if c.klass != "clear"} | set(result.undecided)
    assert all(c.ntc_id not in queued for c in result.cases if c.klass == "clear")


@pytest.mark.data
def test_queue_order(challenge):
    """Class order first, then within a class the margin descending."""
    queue = challenge.slice.result.queue
    assert {item.klass for item in queue} == {"exceeds", "near", "cannot_decide"}  # no clear
    ranks = [gates.CLASS_ORDER.index(item.klass) for item in queue]
    assert ranks == sorted(ranks)
    for stage_rank in {item.stage_rank for item in queue if item.klass == "exceeds"}:
        margins = [
            item.margin_db
            for item in queue
            if item.klass == "exceeds" and item.stage_rank == stage_rank
        ]
        assert margins == sorted(margins, reverse=True)
    assert [item.reason for item in queue if item.klass == "cannot_decide"] == ["no_power"]


@pytest.mark.data
def test_queue_puts_coordination_before_notification(challenge):
    """The stage another administration can still influence comes before a recorded filing."""
    queue = challenge.slice.result.queue
    assert queue[0].stage == "No. 9.1"  # advance publication, rank 0
    for klass in ("exceeds", "near"):
        ranks = [item.stage_rank for item in queue if item.klass == klass]
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

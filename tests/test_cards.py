"""The case card: schema, the golden case 3074-103500417 and the M4 lookup."""

from dataclasses import replace

import pytest

from app.cards import build_card, m4_lookup, render_card_md, results_rows

CARD_FIELDS = (
    "case_id",
    "same_network",
    "source",
    "parties",
    "band",
    "direction",
    "coverage",
    "victim",
    "calculation",
    "m4",
    "class",
    "adjacent",
    "regulatory_stage",
    "threshold_note",
    "missing",
    "next_action",
    "audit",
)


def _audit() -> dict:
    return {
        "input_sha256": "0" * 64,
        "rules_version": "1.1.0",
        "run_at": "2026-11-07T12:00:00+02:00",
    }


def test_mini_card_has_the_whole_schema(mini):
    case = mini.result.case_by_id()["900000001"]
    card = build_card(case, mini.ific, mini.m4, _audit())
    assert set(CARD_FIELDS) <= set(card)
    assert card["case_id"] == "ific-900000001"
    assert card["direction"] == "space-to-Earth"
    assert card["coverage"]["beam_geometry"] == "missing"
    assert card["calculation"]["method"] == "PFD_peak_upper_bound"
    assert card["missing"] == [
        "s_beam.bore_long",
        "s_beam.bore_lat",
        "s_beam.maj_axis",
        "s_beam.min_axis",
    ]
    assert len(card["audit"]["input_sha256"]) == 64
    assert card["victim"]["gain_db"] == 40.0
    assert "900000001" in render_card_md(card)


def test_m4_lookup_is_context_not_a_gate(mini):
    # 3 590-3 610 MHz overlaps both mini sub-bands -> both services, first and last ID
    overlapping = m4_lookup(mini.m4, 3590.0, 3610.0)
    assert overlapping["rows"] == [1, 2]
    assert overlapping["band_mhz"] == [3400.0, 3800.0]
    assert overlapping["services_in_finland"] == "FIXED, MOBILE AND FIXED"
    not_allocated = m4_lookup(mini.m4, 100.0, 200.0)
    assert not_allocated["rows"] == []
    assert not_allocated["services_in_finland"] == "not allocated"


def test_missing_register_field_is_reported(mini):
    """A victim without a gain still gets a card; the gap is named, not guessed."""
    case = mini.result.case_by_id()["900000001"]
    without_gain = replace(
        case,
        victim=replace(case.victim, gain_db=None, power_w=None),
    )
    card = build_card(without_gain, mini.ific, mini.m4, _audit())
    assert "frequencies_of_interest.Ant gain (dB)" in card["missing"]
    assert "frequencies_of_interest.Radioation power" in card["missing"]


def test_results_rows_cover_every_notice(mini):
    cards = [build_card(case, mini.ific, mini.m4, _audit()) for case in mini.result.cases]
    rows = results_rows(mini.result, mini.ific, cards)
    assert len(rows) == len(mini.ific.notices) == 9
    by_id = {row["ntc_id"]: row for row in rows}
    assert by_id["900000005"]["dropped_at"] == "G1"
    assert by_id["900000005"]["reason"] == "earth_station_notice"
    assert by_id["900000005"]["class"] == ""  # dropped before G3: no class
    assert by_id["900000003"]["class"] == "cannot_decide"
    assert by_id["900000003"]["reason"] == "no_orbit"
    assert by_id["900000001"]["class"] == "exceeds"
    assert by_id["900000001"]["dropped_at"] == ""


def test_a_too_large_victim_power_is_flagged(mini):
    """A register row above 1 GW is a synthetic artefact: show it, warn, never hide it."""
    case = mini.result.case_by_id()["900000001"]
    huge = replace(case, victim=replace(case.victim, power_w=7.33e9))
    card = build_card(huge, mini.ific, mini.m4, _audit())
    assert card["victim"]["power_w"] == 7.33e9
    assert "not used in the PFD calculation" in card["synthetic_data_warning"]


def test_a_normal_victim_power_has_no_warning(mini):
    case = mini.result.case_by_id()["900000001"]
    card = build_card(case, mini.ific, mini.m4, _audit())
    assert card["victim"]["power_w"] == 145.0
    assert card["synthetic_data_warning"] is None


@pytest.mark.data
def test_golden_case_103500417(challenge):
    """The plan's test vector, on the real package.

    The band label is 3 642-3 678 MHz, not the 3 662-3 698 MHz in the plan: the CDN beam
    repeats an identical 36 MHz channel every 20 MHz, so ten channels tie for the same
    worst case (same PSD -50,0 dBW/Hz, same gain 28,5 dBi, same station and angle). The code
    keeps the first of the ties in file order. Every number of the vector is reproduced.
    """
    case = challenge.slice.result.case_by_id()["103500417"]
    card = build_card(case, challenge.slice.ific, challenge.slice.m4, _audit())
    assert card["case_id"] == "3074-103500417"
    assert card["class"] == "exceeds"
    assert card["direction"] == "space-to-Earth"
    assert card["same_network"] == ["303500417"]
    assert card["source"]["file"] == "ific3074.mdb"
    assert card["source"]["keys"] == {
        "ntc_id": "103500417",
        "grp_id": "109692106",
        "beam_name": "CDN",
    }
    assert card["parties"]["admin"] == "CHN"
    assert card["band"] == {"freq_min_mhz": 3642.0, "freq_max_mhz": 3678.0, "bandwidth_mhz": 36.0}
    assert card["coverage"]["sat_name"] == "COMPASS-80E"
    assert card["coverage"]["orbit"] == "GSO"
    assert card["coverage"]["longitude_deg"] == 80.0
    assert card["coverage"]["elevation_deg"] == pytest.approx(4.85, abs=0.01)
    assert card["victim"] == {
        "station": "983816",
        "class": "MVV",
        "lat": 65.6981,
        "lon": 24.6245,
        "rx_mhz": 3726.8,
        "gain_db": 40.0,
        "power_w": 145.0,
        "direction_deg": 253.0,
        "directivity": "D",
    }
    calc = card["calculation"]
    assert calc["psd_dbw_hz"] == -50.0
    assert calc["beam_gain_db"] == 28.5
    assert calc["distance_km"] == pytest.approx(41143, abs=1)
    assert calc["fspl_db"] == pytest.approx(163.28, abs=0.01)
    assert calc["pfd_dbw_m2_hz"] == pytest.approx(-184.78, abs=0.01)
    assert calc["limit_dbw_m2_hz"] == pytest.approx(-188.02, abs=0.01)
    assert calc["margin_db"] == pytest.approx(3.24, abs=0.01)
    assert calc["offset_db"] == 0.0
    assert calc["perigee_km"] is None
    assert calc["limit_source"] == (
        "ITU RR 2024 Art. 21 Table 21-4, 3\u00a0400-4\u00a0200 MHz, "
        "FSS (space-to-Earth), GSO, p. 287"
    )
    assert card["m4"] == {
        "rows": [4060, 4091],
        "band_mhz": [3400.0, 3800.0],
        "services_in_finland": "MOBILE AND FIXED",
        "source": "opendata.traficom.fi/api/v13/Taajuusjakotaulukko",
    }
    assert card["missing"] == [
        "s_beam.bore_long",
        "s_beam.bore_lat",
        "s_beam.maj_axis",
        "s_beam.min_axis",
    ]
    assert card["next_action"]["template"] == "templates/correspondence_fi_en.md"
    assert card["next_action"]["question"] == (
        "Can China confirm the service area of the COMPASS-80E CDN beam and whether it "
        "illuminates Finland in the 3\u00a0642-3\u00a0678 MHz range?"
    )
    assert len(card["audit"]["input_sha256"]) == 64
    assert card["audit"]["rules_version"] == "1.1.0"


def test_directive_antenna_gets_a_threshold_note(mini):
    """A high-gain directive victim names the lower trigger level; nothing else changes."""
    case = mini.result.case_by_id()["900000001"]
    assert case.victim.directivity == "ND"  # the mini register has no directive station
    assert build_card(case, mini.ific, mini.m4, _audit())["threshold_note"] is None

    directive = replace(case, victim=replace(case.victim, directivity="D"))
    card = build_card(directive, mini.ific, mini.m4, _audit())
    assert "directive antenna" in card["threshold_note"]
    assert card["class"] == case.klass  # no class change
    assert card["calculation"]["margin_db"] == case.margin_db  # no number change

    low_gain = replace(case, victim=replace(case.victim, directivity="D", gain_db=10.0))
    assert build_card(low_gain, mini.ific, mini.m4, _audit())["threshold_note"] is None


@pytest.mark.data
def test_prov_distribution_and_the_card_stage(challenge):
    """notice.prov is the regulatory stage: the four provisions and their counts, and the card."""
    from collections import Counter

    provs = Counter(notice.prov for notice in challenge.slice.ific.notices.values())
    assert provs == {"9.6": 76, "11.2": 65, "9.1/IA": 50, "RS49": 5}

    case = challenge.slice.result.case_by_id()["103500417"]
    card = build_card(case, challenge.slice.ific, challenge.slice.m4, _audit())
    assert card["regulatory_stage"] == {
        "provision": "No. 11.2",
        "label": "notification recorded in the MIFR",
        "source": "ITU RR 2024, Vol 1, No. 11.2",
    }

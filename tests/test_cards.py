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


@pytest.mark.data
def test_card_has_the_whole_schema(challenge):
    case = challenge.slice.result.case_by_id()["103500417"]
    card = build_card(case, challenge.slice.ific, challenge.slice.m4, _audit())
    assert set(CARD_FIELDS) <= set(card)
    assert card["case_id"] == "3074-103500417"
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
    md = render_card_md(card)
    assert "103500417" in md
    assert f"{card['victim']['lat']:g}".replace(".", ",") in md  # the worst-case station's place
    assert "- **Coverage:**" in md
    assert "s_beam." not in md  # beam geometry is not a blocking gap, the worst case covers it


@pytest.mark.data
def test_m4_lookup_is_context_not_a_gate(challenge):
    # 3 642-3 678 MHz overlaps the 3 400-3 800 MHz M4 allocation -> both rows, one service list
    overlapping = m4_lookup(challenge.slice.m4, 3642.0, 3678.0)
    assert overlapping["rows"] == [4060, 4091]
    assert overlapping["band_mhz"] == [3400.0, 3800.0]
    assert overlapping["services_in_finland"] == "MOBILE AND FIXED"
    not_allocated = m4_lookup(challenge.slice.m4, 500_000.0, 500_100.0)  # above the table
    assert not_allocated["rows"] == []
    assert not_allocated["services_in_finland"] == "not allocated"


@pytest.mark.data
def test_missing_register_field_is_reported(challenge):
    """A victim without a gain still gets a card; the gap is named, not guessed."""
    case = challenge.slice.result.case_by_id()["103500417"]
    without_gain = replace(case, victim=replace(case.victim, gain_db=None, power_w=None))
    card = build_card(without_gain, challenge.slice.ific, challenge.slice.m4, _audit())
    assert "frequencies_of_interest.Ant gain (dB)" in card["missing"]
    assert "frequencies_of_interest.Radioation power" in card["missing"]


@pytest.mark.data
def test_results_rows_cover_every_notice(challenge):
    result = challenge.slice.result
    cards = [
        build_card(case, challenge.slice.ific, challenge.slice.m4, _audit())
        for case in result.cases
    ]
    rows = results_rows(result, challenge.slice.ific, cards)
    assert len(rows) == len(challenge.slice.ific.notices) == 196
    by_id = {row["ntc_id"]: row for row in rows}
    dropped = next(ntc_id for ntc_id, (stage, _) in result.dropped.items() if stage == "G1")
    assert by_id[dropped]["dropped_at"] == "G1"
    assert by_id[dropped]["reason"] == "no_band_overlap"
    assert by_id[dropped]["class"] == ""  # dropped before G3: no class
    assert by_id["126590032"]["class"] == "cannot_decide"
    assert by_id["126590032"]["reason"] == "no_power"
    assert by_id["103500417"]["class"] == "exceeds"
    assert by_id["103500417"]["dropped_at"] == ""


@pytest.mark.data
def test_a_too_large_victim_power_is_flagged(challenge):
    """A register row above 1 GW is a synthetic artefact: show it, warn, never hide it."""
    case = challenge.slice.result.case_by_id()["103500417"]
    huge = replace(case, victim=replace(case.victim, power_w=7.33e9))
    card = build_card(huge, challenge.slice.ific, challenge.slice.m4, _audit())
    assert card["victim"]["power_w"] == 7.33e9
    assert "not used in the PFD calculation" in card["synthetic_data_warning"]


@pytest.mark.data
def test_a_normal_victim_power_has_no_warning(challenge):
    case = challenge.slice.result.case_by_id()["103500417"]
    card = build_card(case, challenge.slice.ific, challenge.slice.m4, _audit())
    assert card["victim"]["power_w"] == 145.0
    assert card["synthetic_data_warning"] is None


@pytest.mark.data
def test_golden_case_103500417(challenge):
    """The plan's test vector, on the real BR IFIC MDB.

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
    assert card["source"]["ific"] == "3074"
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
        "Can China confirm the worst-case PFD the COMPASS-80E CDN beam produces on "
        "Finnish territory in the 3\u00a0642-3\u00a0678 MHz range?"
    )
    assert "service area" not in card["next_action"]["question"]
    assert len(card["audit"]["input_sha256"]) == 64
    assert card["audit"]["rules_version"] == "1.1.0"


@pytest.mark.data
def test_directive_antenna_gets_a_threshold_note(challenge):
    """A high-gain directive victim names the lower trigger level; nothing else changes."""
    case = challenge.slice.result.case_by_id()["103500417"]
    assert case.victim.directivity == "D" and case.victim.gain_db == 40.0
    card = build_card(case, challenge.slice.ific, challenge.slice.m4, _audit())
    assert "directive antenna" in card["threshold_note"]

    low_gain = replace(case, victim=replace(case.victim, gain_db=10.0))
    assert (
        build_card(low_gain, challenge.slice.ific, challenge.slice.m4, _audit())["threshold_note"]
        is None
    )
    non_directive = replace(case, victim=replace(case.victim, directivity="ND"))
    assert (
        build_card(non_directive, challenge.slice.ific, challenge.slice.m4, _audit())[
            "threshold_note"
        ]
        is None
    )


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

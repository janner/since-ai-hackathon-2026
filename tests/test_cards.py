"""The case card: schema, the golden case 3074-103500417 and the M4 lookup."""

from dataclasses import replace
from datetime import date

import pytest

from app.cards import (
    build_card,
    deadline_lines,
    m4_lookup,
    render_card_md,
    render_queue_md,
    results_rows,
)
from app.config import DIRECTIVE_GAIN_DB
from app.gates import GateResult, QueueItem

CARD_FIELDS = (
    "case_id",
    "same_network",
    "source",
    "parties",
    "band",
    "direction",
    "coverage",
    "point",
    "victim",
    "calculation",
    "m4",
    "class",
    "adjacent",
    "deadline",
    "deadline_passed",
    "regulatory_stage",
    "publication",
    "filing_action",
    "filing_follows",
    "threshold_note",
    "missing",
    "next_action",
    "audit",
)


def _audit() -> dict:
    return {
        "input_sha256": "0" * 64,
        "rules_version": "1.2.0",
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
    assert card["calculation"]["limit_a_db"] == -152
    assert card["calculation"]["limit_k_db"] == 10
    assert card["calculation"]["limit_ref_hz"] == 4000
    assert card["publication"] == {
        "refs": [],
        "part": "PART II-S",
        "label": "notification recorded in the MIFR (BR IFIC Part II-S)",
        "sessions": [],
    }
    assert card["missing"] == [
        "s_beam.bore_long",
        "s_beam.bore_lat",
        "s_beam.maj_axis",
        "s_beam.min_axis",
    ]
    assert len(card["audit"]["input_sha256"]) == 64
    md = render_card_md(card)
    assert "103500417" in md
    assert f"{card['point']['lat']:g}".replace(".", ",") in md  # the level point, not a station
    assert "- **Coverage:**" in md
    assert "- **Finland allocation:**" in md
    assert "notification recorded in the MIFR (BR IFIC Part II-S)" in md
    assert "- **Limit row:** A -152 dB(W/m²) at 0–5°, K 10 dB, reference bandwidth 4 kHz" in md
    assert "s_beam." not in md  # beam geometry is not a blocking gap, the worst case covers it


@pytest.mark.data
def test_m4_lookup_names_the_service_and_satellite_use(challenge):
    # 3 642-3 678 MHz overlaps the 3 400-3 800 MHz M4 allocation -> both rows, one service list
    overlapping = m4_lookup(challenge.slice.m4, 3642.0, 3678.0)
    assert overlapping["rows"] == [4060, 4091]
    assert overlapping["band_mhz"] == [3400.0, 3800.0]
    assert overlapping["services_in_finland"] == "MOBILE AND FIXED"
    assert overlapping["satellite_use"] is False  # no satellite service in Finland on the band
    space = m4_lookup(challenge.slice.m4, 18_000.0, 18_100.0)  # FSS space-to-Earth
    assert space["satellite_use"] is True
    uplink_only = m4_lookup(challenge.slice.m4, 6_000.0, 6_010.0)  # FSS Earth-to-space only
    # a downlink in an uplink-only band has no Finnish downlink allocation to sit in (D18)
    assert uplink_only["satellite_use"] is False
    not_allocated = m4_lookup(challenge.slice.m4, 500_000.0, 500_100.0)  # above the table
    assert not_allocated["rows"] == []
    assert not_allocated["services_in_finland"] == "not allocated"
    assert not_allocated["satellite_use"] is False


@pytest.mark.data
def test_m4_lookup_splits_the_band_and_flags_the_part_without_satellite_use(challenge):
    # 3 625-4 200 MHz: MOBILE AND FIXED up to 3 800, FSS space-to-Earth above it.
    split = m4_lookup(challenge.slice.m4, 3625.0, 4200.0)
    assert [(part["lo_mhz"], part["hi_mhz"]) for part in split["segments"]] == [
        (3625.0, 3800.0),
        (3800.0, 4200.0),
    ]
    assert [part["satellite"] for part in split["segments"]] == [False, True]
    assert split["gaps"] == [(3625.0, 3800.0)]
    # One part without a satellite use makes the whole notice a finding.
    assert split["satellite_use"] is False


@pytest.mark.data
def test_m4_lookup_does_not_borrow_a_row_that_only_touches_the_edge(challenge):
    # A band that ends exactly at 3 800 MHz must not pick up the 3 800-4 200 MHz row.
    ends_at_edge = m4_lookup(challenge.slice.m4, 3700.0, 3800.0)
    assert ends_at_edge["satellite_use"] is False
    assert ends_at_edge["gaps"] == [(3700.0, 3800.0)]


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
    case_row = by_id["103500417"]
    assert (case_row["ific"], case_row["case_id"]) == ("3074", "3074-103500417")
    assert case_row["bandwidth_mhz"] == 36.0
    assert case_row["station"] == "986805"
    assert case_row["victim_rx_mhz"] == 3520.5
    assert (by_id[dropped]["ific"], by_id[dropped]["ntc_id"]) == ("3074", dropped)
    assert by_id[dropped]["case_id"] == by_id[dropped]["bandwidth_mhz"] == ""
    assert by_id[dropped]["victim_rx_mhz"] == ""


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
    assert card["victim"]["power_w"] == case.victim.power_w
    assert card["synthetic_data_warning"] is None


@pytest.mark.data
def test_golden_case_103500417(challenge):
    """The plan's test vector, on the real BR IFIC MDB, at the territory edge.

    The CDN beam repeats an identical 36 MHz channel every 20 MHz with the same PSD -50,0
    dBW/Hz and gain 28,5 dBi. Over the whole territory every one of those channels ties, so
    the code keeps the first in file order, 3 442-3 478 MHz. The band label in the plan
    (3 662-3 698 MHz) is one of the ties, not a different case.
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
    assert card["band"] == {"freq_min_mhz": 3442.0, "freq_max_mhz": 3478.0, "bandwidth_mhz": 36.0}
    assert card["coverage"]["sat_name"] == "COMPASS-80E"
    assert card["coverage"]["orbit"] == "GSO"
    assert card["coverage"]["longitude_deg"] == 80.0
    assert card["coverage"]["elevation_deg"] == pytest.approx(4.96, abs=0.01)
    assert card["point"] == {
        "lat": 64.3496,
        "lon": 22.98844,
        "place": "territorial sea outer limit",
    }
    assert card["victim"] == {
        "station": "986805",
        "class": "MVV",
        "lat": 66.1172,
        "lon": 28.5729,
        "rx_mhz": 3520.5,
        "gain_db": 58.0,
        "power_w": 163.0,
        "direction_deg": 82.0,
        "directivity": "D",
    }
    calc = card["calculation"]
    assert calc["psd_dbw_hz"] == -50.0
    assert calc["beam_gain_db"] == 28.5
    assert calc["distance_km"] == pytest.approx(41130, abs=1)
    assert calc["fspl_db"] == pytest.approx(163.28, abs=0.01)
    assert calc["pfd_dbw_m2_hz"] == pytest.approx(-184.78, abs=0.01)
    assert calc["limit_dbw_m2_hz"] == pytest.approx(-188.02, abs=0.01)
    assert calc["margin_db"] == pytest.approx(3.25, abs=0.01)
    assert calc["offset_db"] == 0.0
    assert calc["perigee_km"] is None
    assert calc["limit_source"] == (
        "ITU RR 2024 Art. 21 Table 21-4, 3\u00a0400-4\u00a0200 MHz, "
        "FSS (space-to-Earth), GSO, p. 287"
    )
    assert card["m4"] | {"gaps": None, "segments": None, "notice_gaps": None} == {
        "rows": [4060, 4091],
        "band_mhz": [3400.0, 3800.0],
        "services_in_finland": "MOBILE AND FIXED",
        "satellite_use": False,
        "gaps": None,
        "segments": None,
        "notice_gaps": None,
        "source": "opendata.traficom.fi/api/v13/Taajuusjakotaulukko",
    }
    # The whole notified band has no satellite allocation in Finland, so it is one gap.
    assert card["m4"]["gaps"] == [(3442.0, 3478.0)]
    # The notice repeats the same 36 MHz channel on many rows; the notice-wide gaps merge into
    # one range over the rows this run screened (the slice keeps the rows on the demo band).
    assert card["m4"]["notice_gaps"] == [(3442.0, 3798.0)]
    assert [part["satellite"] for part in card["m4"]["segments"]] == [False]
    assert card["missing"] == [
        "s_beam.bore_long",
        "s_beam.bore_lat",
        "s_beam.maj_axis",
        "s_beam.min_axis",
    ]
    assert card["next_action"]["template"] == "templates/correspondence_fi_en.md"
    assert card["next_action"]["question"] == (
        "Can China confirm the worst-case PFD the COMPASS-80E CDN beam produces on "
        "Finnish territory in the 3\u00a0442-3\u00a0478 MHz range?"
    )
    assert "service area" not in card["next_action"]["question"]
    assert len(card["audit"]["input_sha256"]) == 64
    assert card["audit"]["rules_version"] == "1.2.0"


@pytest.mark.data
def test_directive_antenna_gets_a_threshold_note(challenge):
    """A high-gain directive victim names the lower trigger level; nothing else changes."""
    case = challenge.slice.result.case_by_id()["103500417"]
    assert case.victim.directivity == "D" and case.victim.gain_db >= DIRECTIVE_GAIN_DB
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
        "rank": 1,
    }


@pytest.mark.data
def test_card_carries_the_filing_chain_and_the_queue_action(challenge):
    """103500417 is a modification (act_code M) and follows 100543885, an Art. 9.1 filing."""
    case = challenge.slice.result.case_by_id()["103500417"]
    card = build_card(case, challenge.slice.ific, challenge.slice.m4, _audit())
    assert card["filing_action"] == "M"
    assert card["filing_follows"] == [{"ntc_id": "100543885", "reason": "A"}]
    assert "This filing follows 100543885 (advance publication, No. 9.1)" in render_card_md(card)

    queue = render_queue_md(challenge.slice.result)
    assert "| # | case | class | stage | action | publication |" in queue
    assert "| 103500417 | exceeds | No. 11.2 | M | PART II-S |" in queue


@pytest.mark.data
def test_publication_parts_and_sessions(challenge):
    """pub_ssn names the exact BR IFIC part and session; the card prints both."""
    cr_case = challenge.slice.result.case_by_id()["124520183"]
    cr_card = build_card(cr_case, challenge.slice.ific, challenge.slice.m4, _audit())
    assert cr_card["publication"]["refs"] == ["CR/D", "CR/C"]
    assert cr_card["publication"]["part"] == "CR"
    assert [item["session"] for item in cr_card["publication"]["sessions"]] == ["5378", "6324"]
    md = render_card_md(cr_card)
    assert "coordination request, part D; coordination request, part C (CR/D, CR/C)" in md
    assert "BR IFIC CR/D 5378; CR/C 6324" in md

    api_case = challenge.slice.result.case_by_id()["124545403"]
    api_card = build_card(api_case, challenge.slice.ific, challenge.slice.m4, _audit())
    assert api_card["publication"]["refs"] == ["API/B", "API/A"]
    assert api_card["publication"]["part"] == "API"
    assert (
        "advance publication, part B; advance publication, part A (API/B, API/A)"
        in render_card_md(api_card)
    )


def test_deadline_line_marks_a_passed_deadline():
    """The card's Resolution 35 line shows the date; a passed deadline is marked, not hidden."""
    assert deadline_lines({"deadline": "19.12.2026", "deadline_passed": False}) == [
        "- **Resolution 35 deadline:** 19.12.2026"
    ]
    assert deadline_lines({"deadline": "18.12.2019", "deadline_passed": True}) == [
        "- **Resolution 35 deadline:** 18.12.2019 (passed)"
    ]
    assert deadline_lines({"deadline": None, "deadline_passed": False}) == []


def test_queue_md_carries_a_deadline_column():
    """Synthetic queue: the deadline column shows the date, marks a passed one, else `-`."""
    queue = [
        QueueItem("1", "exceeds", "exceeds", 1.0, deadline=date(2026, 12, 19)),
        QueueItem(
            "2", "exceeds", "exceeds", 2.0, deadline=date(2019, 12, 18), deadline_passed=True
        ),
        QueueItem("3", "exceeds", "exceeds", 3.0),
    ]
    result = GateResult(
        cases=[],
        undecided={},
        dropped={},
        queue=queue,
        counts={"notices": 3, "g1": 3, "g2": 3, "g3": 3, "cannot_decide": 0},
    )
    md = render_queue_md(result)
    assert "| # | case | class | stage | action | publication | deadline | margin dB |" in md
    assert "| 1 | 1 | exceeds |  | - | - | 19.12.2026 |" in md
    assert "| 2 | 2 | exceeds |  | - | - | 18.12.2019 (passed) |" in md
    assert "| 3 | 3 | exceeds |  | - | - | - |" in md


@pytest.mark.data
def test_the_demo_card_shows_its_res35_deadline(challenge):
    """125500277's group falls due on 19 Dec 2026; the card line carries it, a passed one is
    marked, and a case without a deadline gets no line."""
    result = challenge.slice.result
    assert {case.ntc_id for case in result.cases if case.deadline} == {"125500277"}
    case = result.case_by_id()["125500277"]
    card = build_card(case, challenge.slice.ific, challenge.slice.m4, _audit())
    assert card["deadline"] == "19.12.2026"
    assert card["deadline_passed"] is False
    assert "- **Resolution 35 deadline:** 19.12.2026" in render_card_md(card)

    past = replace(case, deadline=date(2019, 12, 18), deadline_passed=True)
    past_card = build_card(past, challenge.slice.ific, challenge.slice.m4, _audit())
    assert past_card["deadline"] == "18.12.2019" and past_card["deadline_passed"] is True
    assert "- **Resolution 35 deadline:** 18.12.2019 (passed)" in render_card_md(past_card)

    without = replace(case, deadline=None, deadline_passed=False)
    assert "- **Resolution 35 deadline:**" not in render_card_md(
        build_card(without, challenge.slice.ific, challenge.slice.m4, _audit())
    )

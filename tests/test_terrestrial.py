import math
from collections import Counter
from pathlib import Path

import pytest

from app import ingest
from app import terrestrial as t

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TIFC = DATA / "itu-terr-ific"
MDB_CURR = TIFC / "brific3076.mdb"
MDB_PREV = TIFC / "brific3075.mdb"
REGISTER = DATA / "frequencies_of_interest.csv"

# The real BR IFIC MDBs are never committed: without them the data tests skip.
needs_mdb = pytest.mark.skipif(
    not (MDB_CURR.is_file() and MDB_PREV.is_file() and REGISTER.is_file()),
    reason="BR IFIC 3075/3076 MDB missing: run scripts/fetch_data.py",
)


def _notice(**overrides):
    """One land-mobile notice, in the shape load_issue_mdb() returns."""
    notice = {
        "terrakey": "1",
        "adm_ref_id": "EST-1",
        "adm": "EST",
        "stn_cls": "FB",
        "intent": "ADD",
        "freq_min_mhz": 450.0,
        "freq_max_mhz": 455.0,
        "lat": 59.4,
        "lon": 24.7,
        "p_erp_kw": 10.0,
        "ant_h_m": 30.0,
    }
    notice.update(overrides)
    return notice


def _issue(notices, issue="X", counts=None):
    return {
        "issue": issue,
        "file": f"brific{issue}.mdb",
        "sha256": "0" * 64,
        "path": Path("/dev/null"),  # not a file: input_digest skips it
        "notices": notices,
        "intent_counts": counts or Counter(n["intent"] for n in notices),
        "skipped_invalid": {},
    }


def _register(tmp_path):
    path = tmp_path / "register.csv"
    path.write_text(
        "Station number,Class of licence,Latitude,Longitude,Channel bandwidth,"
        "RX frequency,TX frequency\n"
        "1,BC,60.2,24.9,25 kHz,454.0 MHz,464.04 MHz\n",
        encoding="utf-8",
    )
    return path


def test_diff_intents_reads_the_intent_field():
    issue = {"intent_counts": {"ADD": 5, "MODIFY": 2, "SUPPRESS": 1, "RECORDED": 3}}
    assert t.diff_intents(issue) == {
        "counts": {"ADD": 5, "MODIFY": 2, "SUPPRESS": 1, "RECORDED": 3},
        "new": 5,
        "modified": 2,
        "withdrawn": 1,
        "recorded": 3,
    }


def test_filter_keeps_land_mobile_in_reach():
    notices = [
        _notice(terrakey="1"),  # in the register, within 1 000 km
        _notice(terrakey="2", stn_cls="FX"),  # fixed, not land mobile
        _notice(terrakey="3", lat=-33.9, lon=18.4),  # Cape Town, 10 000 km away
        _notice(terrakey="4", freq_min_mhz=900.0, freq_max_mhz=905.0),  # no register overlap
        _notice(terrakey="5", adm="FIN"),  # Finland's own assignment
        # no register overlap, but fxm_coord names FIN as affected: always kept
        _notice(
            terrakey="6",
            freq_min_mhz=791.0,
            freq_max_mhz=796.0,
            coord=[("4.2.2.2", "FIN", "COORD REQUIRED", "ITU"), ("RR6.7", "EST", "X", "Y")],
        ),
    ]
    kept, dropped = t.select(notices, [454.0])
    assert [n["terrakey"] for n, _ in kept] == ["1", "6"]
    assert dropped == {"own": 1, "far": 1, "class": 1, "no_band_overlap": 1}
    assert t.coord_fin(notices[5]) == ["4.2.2.2: COORD REQUIRED (ITU)"]


def test_a_notice_naming_finland_in_fxm_coord_shows_why_it_was_kept(tmp_path):
    notice = _notice(
        freq_min_mhz=791.0, freq_max_mhz=796.0, coord=[("4.2.2.2", "FIN", "COORD REQUIRED", "ITU")]
    )
    doc = t.findings(_issue([notice]), _issue([notice]), _register(tmp_path))
    finding = doc["notices"][0]
    assert finding["coord_fin"] is True
    assert finding["coord_provisions"] == ["4.2.2.2"]
    assert finding["kept_because"] == [
        "Finland listed as affected administration (fxm_coord: 4.2.2.2: COORD REQUIRED (ITU))"
    ]
    assert doc["summary"]["coord_fin_kept"] == 1


def test_trends_group_by_adm_band_class_width():
    prev = [_notice(terrakey="1")]
    curr = [
        _notice(terrakey="2", intent="ADD"),
        _notice(terrakey="3", intent="MODIFY"),
        _notice(terrakey="9", intent="RECORDED"),  # the stock, not a change
    ]
    rows = t.trends(prev, curr)
    assert len(rows) == 1
    row = rows[0]
    assert (row["new"], row["modified"], row["withdrawn"], row["prev_count"]) == (1, 1, 0, 1)
    assert row["neighbour"] is True  # EST


def test_anomalies_are_neighbours_only_with_a_reason():
    far = [_notice(terrakey=str(i), adm="SVN", lat=46.0, lon=14.5) for i in range(3)]
    near = [_notice(terrakey=str(10 + i), adm="RUS", lat=60.9, lon=29.5) for i in range(3)]
    rows = t.trends([], far + near)
    assert [r["adm"] for r in rows] == ["RUS", "SVN"]  # neighbours first
    found = t.anomalies(rows)
    assert [r["adm"] for r in found] == ["RUS"]
    assert "3 new now" in found[0]["reason"]


def test_findings_applies_the_tr2508_threshold(tmp_path):
    issue = _issue([_notice()])
    doc = t.findings(issue, issue, _register(tmp_path))
    assert doc["coordination_thresholds"]["rows"][-1] == {
        "f_min_mhz": 470.0,
        "f_max_mhz": 10000.0,
        "dbuv_m": 20.0,
    }
    assert "T/R 25-08" in doc["criterion"] and "border line" in doc["criterion"]
    assert doc["source"]["file"] == issue["file"]
    assert doc["source"]["keys"] == ["terrakey", "adm_ref_id"]
    assert doc["diff"]["new"] == 1
    finding = doc["notices"][0]
    assert finding["ific"] == "X"
    assert finding["terrakey"] == "1"
    assert finding["adm_ref_id"] == "EST-1"
    assert finding["intent"] == "ADD"
    assert finding["tables"] == ["fxm_terra", "fxm_geo", "fxm_ant", "fxm_coord"]
    assert (finding["tx_lat"], finding["tx_lon"]) == (59.4, 24.7)
    assert finding["border"]["distance_km"] > 0
    assert finding["bandwidth_source"] == "freq_max - freq_min"  # no bdwdth in the fixture
    assert (
        "Table 21-4" not in doc["criterion"]
        and "national M4 value not confirmed" in (doc["criterion"])
    )
    # 450-455 MHz is a 5 MHz channel: A1.2.3 adds 10*log10(5000/25) to the 20 dB(uV/m) base.
    assert finding["threshold_dbuv_m"] == pytest.approx(20.0 + 10 * math.log10(200.0))
    assert finding["coordination"] is not None
    assert finding["border"]["samples"] == len(t.border_samples())


def test_findings_carry_the_same_provenance_contract_as_a_space_card(tmp_path):
    """Both outputs carry source.file/sha256, audit.* and missing; only the class differs."""
    issue = _issue([_notice()])
    doc = t.findings(issue, issue, _register(tmp_path))
    assert set(doc["source"]) == {"file", "sha256", "tables", "keys"}
    assert set(doc["prev_source"]) == {"file", "sha256", "tables", "keys"}
    assert len(doc["source"]["sha256"]) == 64
    assert set(doc["audit"]) == {"input_sha256", "rules_version", "run_at"}
    assert len(doc["audit"]["input_sha256"]) == 64
    assert doc["audit"]["rules_version"] and doc["audit"]["run_at"]
    assert "missing" in doc


def test_params_say_what_the_field_strength_is_computed_for(tmp_path):
    """The old text claimed a 1 kW basis while the value uses the notice's own power."""
    issue = _issue([_notice()])
    text = t.findings(issue, issue, _register(tmp_path))["params"]["field_strength_for"]
    assert "1 kW" not in text
    assert "band centre" in text and "p_erp_kw" in text and "ant_h_m" in text


def test_field_strength_matches_p1546_table_node():
    # Py1546 at 10 % time: 28.89 dB(uV/m) for 600 MHz, 50 km, h1 37.5 m (1 kW ERP).
    assert t.field_strength_p1546(600, 50, 37.5, 1.0) == pytest.approx(28.89, abs=0.01)


def test_field_strength_interpolates_logarithmically_per_annex_5():
    # The geometric mean of two nodes is the arithmetic mean of their values (log f, log h1).
    f_mid = math.sqrt(100 * 600)
    assert t.field_strength_p1546(f_mid, 50, 20, 1.0) == pytest.approx((30.72 + 25.23) / 2)
    h_mid = math.sqrt(20 * 37.5)
    assert t.field_strength_p1546(600, 50, h_mid, 1.0) == pytest.approx((25.23 + 28.89) / 2)
    # Below 100 MHz the frequency is extrapolated from the 100 and 600 MHz curves.
    assert t.field_strength_p1546(50, 50, 20, 1.0) > t.field_strength_p1546(100, 50, 20, 1.0)


def test_field_strength_falls_with_distance_and_follows_power():
    values = [t.field_strength_p1546(450, d, 40, 1.0) for d in (1, 10, 50, 200, 600, 1000)]
    assert all(a > b for a, b in zip(values, values[1:], strict=False))
    low = t.field_strength_p1546(450, 80, 40, 1.0)
    high = t.field_strength_p1546(450, 80, 40, 10.0)
    assert high - low == pytest.approx(10.0, abs=0.01)


def test_field_strength_rejects_unusable_input():
    assert t.field_strength_p1546(450, 0, 40, 1.0) is None
    assert t.field_strength_p1546(450, 80, 40, 0.0) is None
    assert t.field_strength_p1546(450, 80, None, 1.0) is None


def test_extrapolated_flags_clamped_query():
    assert t.extrapolated(450, 80, 40) is False
    assert t.extrapolated(50, 900, 40) is True  # below the frequency axis
    assert t.extrapolated(450, 1200, 40) is True  # beyond the distance axis
    assert t.extrapolated(450, 80, 2000) is True  # above the height axis
    assert t.extrapolated(450, 0.5, 40) is True  # below the distance axis


def test_extrapolated_follows_the_point_that_gives_the_maximum(tmp_path):
    """A notice deep in Poland has border samples beyond 1000 km toward Lapland, but its
    maximum sits on the Baltic inside the table: no flag. A 5 m antenna is below the table."""
    far_samples = _issue([_notice(terrakey="1", lat=52.0, lon=19.0)])
    doc = t.findings(far_samples, far_samples, _register(tmp_path))
    assert doc["notices"][0]["extrapolated"] is False
    low = _issue([_notice(ant_h_m=5.0)])
    finding = t.findings(low, low, _register(tmp_path))["notices"][0]
    assert finding["extrapolated"] is True
    assert "clamped to 10 m" in finding["assumptions"][0]


def test_a_notice_without_antenna_height_uses_the_stated_assumption(tmp_path):
    """Mobile stations carry no height: 10 m is assumed, stated and still decided."""
    issue = _issue([_notice(ant_h_m=None)])
    doc = t.findings(issue, issue, _register(tmp_path))
    finding = doc["notices"][0]
    assert finding["ant_h_m"] is None and finding["ant_h_used_m"] == 10.0
    assert "hgt_agl missing" in finding["assumptions"][0]
    assert finding["border"]["max_dbuv_m"] is not None
    assert "oletetaan 10 m" in t.render_md(doc)


def test_an_uncomputable_notice_is_undecided_never_clear(tmp_path):
    """No T/R 25-08 row below 29.7 MHz: coordination is None with the reason, not False."""
    notice = _notice(
        freq_min_mhz=20.0, freq_max_mhz=20.1, coord=[("RR6.7", "FIN", "COORD REQUIRED", "ITU")]
    )
    doc = t.findings(_issue([notice]), _issue([notice]), _register(tmp_path))
    finding = doc["notices"][0]
    assert finding["coordination"] is None
    assert "threshold_dbuv_m" in finding["empty_reason"]
    assert doc["summary"]["undecided"] == 1
    assert "ratkaisematta" in t.render_md(doc)


def test_bandwidth_comes_from_bdwdth_when_present():
    notice = _notice(freq_min_mhz=152.89, freq_max_mhz=152.91, bdwdth_khz=50.0)
    assert t._bandwidth(notice) == (50.0, "fxm_terra.bdwdth")
    assert t._bandwidth(_notice()) == (5000.0, "freq_max - freq_min")
    assert t.tr2508_threshold(152.9, t._bandwidth(notice)[0]) == pytest.approx(
        12.0 + 10 * math.log10(2.0)
    )


def test_tr2508_threshold_is_frequency_dependent_and_bandwidth_corrected():
    assert t.tr2508_threshold(30) == 0.0
    assert t.tr2508_threshold(100) == 6.0
    assert t.tr2508_threshold(152.9) == 12.0
    assert t.tr2508_threshold(390) == 18.0
    assert t.tr2508_threshold(450) == 20.0
    assert t.tr2508_threshold(470) == 20.0
    # Traficom 7.11.2026: above 470 MHz the same criterion as the 400-470 MHz range
    assert t.tr2508_threshold(500) == 20.0
    assert t.tr2508_threshold(818.5) == 20.0
    assert t.tr2508_threshold(29.0) is None  # below 29.7 MHz
    # narrower than the 25 kHz reference: no conversion (A1.2.3 applies within 25 kHz)
    assert t.tr2508_threshold(152.9, 16.0) == 12.0
    # wider channel: BC = 10*log10(bw / 25 kHz)
    assert t.tr2508_threshold(152.9, 50.0) == pytest.approx(12.0 + 10 * math.log10(2.0))
    assert t.tr2508_threshold(818.5, 5000.0) == pytest.approx(20.0 + 10 * math.log10(200.0))


def test_distance_to_border_is_a_line_not_four_points():
    # Helsinki sits ~13 km inside the 12 nm territorial sea line, not on a test point
    assert t.distance_to_border_km(60.1699, 24.9384) < 20
    assert 700 < t.distance_to_border_km(55.7558, 37.6173) < 900  # Moscow
    assert t.distance_to_border_km(-33.9, 18.4) > 9000  # Cape Town
    # Maarianhamina is inside the 12 nm line around Åland, ~25 km from it
    assert 15 < t.distance_to_border_km(60.0971, 19.9348) < 40


def test_border_samples_cover_the_line_evenly():
    lines = t.border_line()
    samples = t.border_samples()
    # Four polylines: SE, NO, RU land borders and the closed TS territorial-sea ring.
    assert len(lines) == 4
    assert len(samples) > 100
    steps = [
        t.haversine_km(a[0], a[1], b[0], b[1]) for a, b in zip(samples, samples[1:], strict=False)
    ]
    # The only allowed gap is the jump between two separate polylines.
    gaps = [s for s in steps if s > 2 * t.BORDER_STEP_KM]
    assert len(gaps) <= len(lines)


def test_border_sections_cover_the_ring_and_pick_the_max_section(tmp_path):
    """The split must cover every section, and the section with the strongest
    value must be the one the notice's nearest border stretch belongs to."""
    assert set(s for _, _, s in t.border_samples()) == {"SE", "NO", "RU", "TS"}
    # A notice just outside Lappeenranta faces the Russian border, so RU holds the maximum.
    notice = _notice(freq_min_mhz=450.0, freq_max_mhz=455.0, lat=60.9, lon=29.5)
    issue = _issue([notice])
    finding = t.findings(issue, issue, _register(tmp_path))["notices"][0]
    border = finding["border"]
    assert border["section"] == "RU"
    assert border["max_dbuv_m"] == max(v for v in border["sections"].values() if v is not None)
    # The section maxima are part of the output and the markdown shows them.
    markdown = t.render_md(t.findings(issue, issue, _register(tmp_path)))
    assert "rajaosat" in markdown and "## Kenttävoimakkuus rajaosittain" in markdown


def test_flag_stations_reports_the_strongest_notice_per_station():
    station = {
        "station": "1",
        "lat": 61.0,
        "lon": 28.5,
        "freq_mhz": 152.9,
        "freqs_mhz": [152.9],
        "bw_khz": 25.0,
        "stn_cls": "FX",
    }
    far = {**station, "station": "2", "lat": 65.0, "lon": 25.0}
    kept = [
        (
            _notice(
                freq_min_mhz=152.89,
                freq_max_mhz=152.91,
                lat=60.9,
                lon=28.4,
                p_erp_kw=1.0,
                ant_h_m=30.0,
            ),
            20.0,
        )
    ]
    rows = t.flag_stations(kept, [station, far])
    assert [r["station"] for r in rows] == ["1", "2"]  # sorted by margin, strongest first
    assert rows[0]["threshold_dbuv_m"] == 12.0
    assert rows[0]["e_dbuv_m"] > rows[1]["e_dbuv_m"]
    # a channel the notice band does not overlap is not evaluated
    assert (
        t.flag_stations([(_notice(freq_min_mhz=800.0, freq_max_mhz=805.0), 10.0)], [station]) == []
    )
    # above 470 MHz the same criterion applies (Traficom 7.11.2026): 20 dB(uV/m) + BC
    hf_station = {**station, "station": "3", "freq_mhz": 802.0, "freqs_mhz": [802.0]}
    hf = _notice(
        freq_min_mhz=800.0, freq_max_mhz=805.0, lat=60.9, lon=28.4, p_erp_kw=1.0, ant_h_m=30.0
    )
    rows3 = t.flag_stations([(hf, 10.0)], [hf_station])
    assert rows3[0]["threshold_dbuv_m"] == pytest.approx(20.0 + 10 * math.log10(5000 / 25))


def test_register_stations_reads_location_and_channel_bandwidth(tmp_path):
    stations = t.register_stations(_register(tmp_path))
    assert len(stations) == 1
    assert stations[0]["station"] == "1"
    assert (stations[0]["lat"], stations[0]["lon"]) == (60.2, 24.9)
    assert stations[0]["freqs_mhz"] == [454.0, 464.04]
    assert stations[0]["bw_khz"] == 25.0


def test_run_writes_three_outputs(tmp_path):
    issue = _issue([_notice(terrakey="1"), _notice(terrakey="2", intent="SUPPRESS")])
    out = tmp_path / "out"
    doc = t.run(issue, issue, _register(tmp_path), out)
    assert {p.name for p in out.iterdir()} == {
        "terrestrial_findings.json",
        "terrestrial_trends.csv",
        "TERRESTRIAL.md",
    }
    rows = (out / "terrestrial_trends.csv").read_text(encoding="utf-8").splitlines()
    assert len(rows) == len(doc["trends"]) + 1
    markdown = (out / "TERRESTRIAL.md").read_text(encoding="utf-8")
    assert "fxm_terra, fxm_geo, fxm_ant" in markdown and "ECC T/R 25-08" in markdown


def test_load_issue_mdb_rejects_a_missing_file(tmp_path):
    with pytest.raises(ValueError, match="löytynyt"):
        t.load_issue_mdb(tmp_path / "none.mdb")


def test_cli_fails_cleanly_on_missing_input(tmp_path):
    with pytest.raises(SystemExit, match="terrestrial:"):
        t.main(
            [
                "--prev",
                str(tmp_path / "none.mdb"),
                "--curr",
                str(tmp_path / "none.mdb"),
                "--register",
                str(_register(tmp_path)),
                "--out",
                str(tmp_path / "out"),
            ]
        )


def test_register_counts_both_rx_and_tx_directions(tmp_path):
    """A channel is a pair: RX 454.0 MHz and TX 464.04 MHz belong to the same licence."""
    freqs = t.register_frequencies(_register(tmp_path))
    assert 454.0 in freqs and 464.04 in freqs and len(freqs) == 2


def test_register_without_frequency_columns_is_rejected(tmp_path):
    path = tmp_path / "register.csv"
    path.write_text("Station number,Class of licence\n1,MVV\n", encoding="utf-8")
    with pytest.raises(ValueError, match="taajuussaraketta"):
        t.register_frequencies(path)


@pytest.fixture(scope="module")
def issue3076():
    return t.load_issue_mdb(MDB_CURR)


@pytest.fixture(scope="module")
def issue3075():
    return t.load_issue_mdb(MDB_PREV)


@pytest.mark.data
@needs_mdb
def test_real_3076_intent_distribution_and_source(issue3076):
    assert issue3076["intent_counts"] == {
        "ADD": 2905,
        "MODIFY": 163,
        "SUPPRESS": 413,
        "RECORDED": 576,
    }
    assert t.diff_intents(issue3076)["new"] == 2905
    assert issue3076["issue"] == "3076"
    assert issue3076["file"] == "brific3076.mdb"
    assert issue3076["sha256"] == ingest.sha256(MDB_CURR)
    assert issue3076["skipped_invalid"] == {"power": 31, "location": 9}


@pytest.mark.data
@needs_mdb
def test_real_3076_russian_federation_notices(issue3076):
    rus = [n for n in issue3076["notices"] if n["adm"] == "RUS"]
    assert len(rus) == 313
    assert Counter(n["stn_cls"] for n in rus) == {"FX": 188, "ML": 68, "FB": 57}


@pytest.mark.data
@needs_mdb
def test_real_mdb_prints_the_example_finding(issue3075, issue3076, tmp_path):
    """The example in the handoff: POL 92817506 at 801-806 MHz, 43 dB(uV/m) with the extension."""
    doc = t.run(issue3075, issue3076, REGISTER, tmp_path)
    assert len(doc["notices"]) == 32
    assert doc["summary"] == {
        "in_reach": 32,
        "above_threshold": 6,
        "undecided": 0,
        "with_assumptions": 2,
        "coord_fin_kept": 11,
    }
    assert doc["filter"]["dropped"]["own"] == 4
    # Kept only because fxm_coord names FIN (no register overlap): the audit cases.
    by_key = {n["terrakey"]: n for n in doc["notices"]}
    for key in ("93005610", "93082392", "93082323", "92326149"):
        assert by_key[key]["coord_fin"] is True
    assert by_key["93005610"]["coord_fin_rows"][0].startswith("4.2.2.2: COORD REQUIRED")
    assert len(doc["anomalies"]) <= 5 and all(a["neighbour"] for a in doc["anomalies"])
    assert doc["diff"]["counts"]["ADD"] == 2905
    assert doc["missing"] == {"power": 31, "location": 9}
    assert doc["missing_prev"] == {"power": 19, "location": 6}
    finding = next(n for n in doc["notices"] if n["terrakey"] == "92817506")
    assert finding["adm"] == "POL" and finding["band"] == "801-806 MHz"
    # 10 % time curves, max on the 12 nm territorial-sea line ~625 km away.
    assert finding["border"]["max_dbuv_m"] == pytest.approx(-38.1, abs=0.2)
    assert finding["bandwidth_source"] == "fxm_terra.bdwdth"
    assert finding["border"]["section"] == "TS"
    # 803.5 MHz: Traficom extends the 400-470 MHz criterion above 470 MHz, 5 MHz channel
    assert finding["threshold_dbuv_m"] == pytest.approx(20.0 + 10 * math.log10(200.0))
    assert finding["coordination"] is False
    assert (tmp_path / "TERRESTRIAL.md").exists()


@pytest.mark.data
@needs_mdb
def test_real_run_flags_the_vhf_stations_above_the_threshold(issue3075, issue3076, tmp_path):
    """At 10 % time four Finnish VHF stations exceed 12 dB(uV/m) from the RUS 152-153 MHz notices
    (Py1546 at 10 % gives 16.5 / 14.7 / 12.4 / 12.1 dB(uV/m) for these points)."""
    doc = t.run(issue3075, issue3076, REGISTER, tmp_path)
    rows = doc["flagged_stations"]["stations"]
    assert rows and rows[0]["threshold_dbuv_m"] == 12.0
    assert rows[0]["station"] == "614221"
    assert rows[0]["e_dbuv_m"] == pytest.approx(16.5, abs=0.2)
    assert [r["station"] for r in rows if r["exceeds"]] == ["614221", "617699", "601062", "615366"]
    assert doc["flagged_stations"]["count"] == 4


@pytest.mark.data
@needs_mdb
def test_cli_runs_on_the_real_mdb(issue3075, issue3076, tmp_path, capsys):
    out = tmp_path / "out"
    code = t.main(
        [
            "--prev",
            str(MDB_PREV),
            "--curr",
            str(MDB_CURR),
            "--register",
            str(REGISTER),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    assert "2905 new, 163 modified, 413 withdrawn, 576 recorded" in capsys.readouterr().out
    assert (out / "TERRESTRIAL.md").exists()

from collections import Counter
from pathlib import Path

import pytest

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
        "source": f"{issue} sha256:0",
        "notices": notices,
        "intent_counts": counts or Counter(n["intent"] for n in notices),
        "skipped_invalid": {},
    }


def _register(tmp_path):
    path = tmp_path / "register.csv"
    path.write_text(
        "Station number,RX frequency,TX frequency\n1,454.0 MHz,464.04 MHz\n", encoding="utf-8"
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
    ]
    kept, dropped = t.select(notices, [454.0])
    assert [n["terrakey"] for n, _ in kept] == ["1"]
    assert dropped == {"far": 1, "class": 1, "no_band_overlap": 1}


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


def test_findings_leaves_threshold_open_and_cites_the_source(tmp_path):
    issue = _issue([_notice()])
    doc = t.findings(issue, issue, _register(tmp_path))
    assert doc["protection_threshold_dbuVm"] is None
    assert "to be confirmed" in doc["criterion"]
    assert doc["source"] == issue["source"]
    assert doc["diff"]["new"] == 1
    finding = doc["notices"][0]
    assert finding["ific"] == "X"
    assert finding["terrakey"] == "1"
    assert finding["intent"] == "ADD"
    assert finding["tables"] == ["fxm_terra", "fxm_geo", "fxm_ant"]


def test_params_say_what_the_field_strength_is_computed_for(tmp_path):
    """The old text claimed a 1 kW basis while the value uses the notice's own power."""
    issue = _issue([_notice()])
    text = t.findings(issue, issue, _register(tmp_path))["params"]["field_strength_for"]
    assert "1 kW" not in text
    assert "band centre" in text and "p_erp_kw" in text and "ant_h_m" in text


def test_field_strength_matches_p1546_table_node():
    # ITU:n referenssitoteutus (Py1546) antaa 26.15 dB(uV/m) pisteelle 600 MHz, 50 km, h1 37.5 m.
    assert t.field_strength_p1546(600, 50, 37.5, 1.0) == pytest.approx(26.15, abs=0.01)


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


def test_findings_flags_extrapolated_per_point(tmp_path):
    """The flag must follow the worst point: near Maarianhamina is inside the table,
    Lappeenranta is beyond its 1000 km edge, so the notice is extrapolated."""
    notice = _notice(terrakey="1", lat=52.0, lon=19.0)
    issue = _issue([notice])
    doc = t.findings(issue, issue, _register(tmp_path))
    assert len(doc["notices"]) == 1
    assert doc["notices"][0]["extrapolated"] is True


def test_a_notice_without_antenna_height_gets_no_value(tmp_path):
    """Mobile stations carry no height; the row is reported with a dash, not a guess."""
    issue = _issue([_notice(ant_h_m=None)])
    doc = t.findings(issue, issue, _register(tmp_path))
    assert doc["notices"][0]["ant_h_m"] is None
    assert all(p["e_dbuv_m"] is None for p in doc["notices"][0]["points"].values())


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
    assert issue3076["source"].startswith("brific3076.mdb sha256:")


@pytest.mark.data
@needs_mdb
def test_real_3076_russian_federation_notices(issue3076):
    rus = [n for n in issue3076["notices"] if n["adm"] == "RUS"]
    assert len(rus) == 313
    assert Counter(n["stn_cls"] for n in rus) == {"FX": 188, "ML": 68, "FB": 57}


@pytest.mark.data
@needs_mdb
def test_real_mdb_prints_the_example_finding(issue3075, issue3076, tmp_path):
    """The example in the handoff: POL 92817506 at 801-806 MHz, Maarianhamina -53.0."""
    doc = t.run(issue3075, issue3076, REGISTER, tmp_path)
    assert len(doc["notices"]) == 28
    assert doc["diff"]["counts"]["ADD"] == 2905
    finding = next(n for n in doc["notices"] if n["terrakey"] == "92817506")
    assert finding["adm"] == "POL" and finding["band"] == "801-806 MHz"
    assert finding["points"]["Maarianhamina"]["e_dbuv_m"] == pytest.approx(-53.0, abs=0.05)
    assert (tmp_path / "TERRESTRIAL.md").exists()


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

import json
from pathlib import Path

import pytest

from app import terrestrial as t

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE = FIXTURES / "terrestrial_fixture.json"
REGISTER = FIXTURES / "register_terrestrial_mini.csv"
REAL_REGISTER = Path(__file__).resolve().parent.parent / "data" / "frequencies_of_interest.csv"


@pytest.fixture(scope="module")
def issues():
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    prev, curr = doc["issues"]
    return prev, curr


def test_diff_finds_new_modified_withdrawn(issues):
    prev, curr = issues
    changes = t.diff_issues(prev, curr)
    counts = {
        kind: sum(1 for c in changes if c["change"] == kind)
        for kind in ("new", "modified", "withdrawn")
    }
    assert counts == {"new": 3, "modified": 1, "withdrawn": 1}
    modified = next(c for c in changes if c["change"] == "modified")
    assert modified["ntc_id"] == "1090006"
    assert modified["fields"] == ["p_erp_kw"]


def test_diff_detects_moved_station(issues):
    prev, curr = issues
    moved = json.loads(json.dumps(curr))
    moved["notices"][0]["lat"] += 0.5
    changes = t.diff_issues(prev, moved)
    change = next(c for c in changes if c["ntc_id"] == "1090001")
    assert change["change"] == "modified"
    assert change["fields"] == ["lat"]


def test_filter_drops_far_and_non_land_mobile(issues):
    _, curr = issues
    kept, dropped = t.select(curr["notices"], t.register_frequencies(REGISTER))
    assert dropped == {"far": 1, "class": 1, "no_band_overlap": 0}
    assert [n["ntc_id"] for n, _ in kept] == [
        n["ntc_id"] for n in curr["notices"] if n["ntc_id"] not in {"1090100", "1090101"}
    ]


def test_findings_mark_synthetic_and_leave_threshold_open(issues, tmp_path):
    prev, curr = issues
    doc = t.findings(prev, curr, REGISTER)
    assert doc["source"] == "synthetic_fixture"
    assert doc["synthetic"] is True
    assert doc["protection_threshold_dbuVm"] is None
    assert "to be confirmed" in doc["criterion"]
    assert doc["notices"] and not any(n["extrapolated"] for n in doc["notices"])


def test_params_say_what_the_field_strength_is_computed_for(issues):
    """The old text claimed a 1 kW basis while the value uses the notice's own power."""
    prev, curr = issues
    text = t.findings(prev, curr, REGISTER)["params"]["field_strength_for"]
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


def test_findings_flags_extrapolated_per_point():
    """The flag must follow the worst point: near Maarianhamina is inside the table,
    Lappeenranta is beyond its 1000 km edge, so the notice is extrapolated."""
    issue = {
        "issue": "X",
        "notices": [
            {
                "ntc_id": "1",
                "adm": "EST",
                "stn_cls": "LM",
                "freq_min_mhz": 450,
                "freq_max_mhz": 460,
                "lat": 52.0,
                "lon": 19.0,
                "p_erp_kw": 10,
                "ant_h_m": 30,
            }
        ],
    }
    doc = t.findings(issue, issue, REGISTER)
    assert len(doc["notices"]) == 1
    assert doc["notices"][0]["extrapolated"] is True


def test_run_writes_three_outputs(issues, tmp_path):
    prev, curr = issues
    doc = t.run(prev, curr, REGISTER, tmp_path)
    files = {p.name for p in tmp_path.iterdir()}
    assert files == {"terrestrial_findings.json", "terrestrial_trends.csv", "TERRESTRIAL.md"}
    written = json.loads((tmp_path / "terrestrial_findings.json").read_text(encoding="utf-8"))
    assert written["diff"]["new"] == doc["diff"]["new"] == 3
    rows = (tmp_path / "terrestrial_trends.csv").read_text(encoding="utf-8").splitlines()
    assert len(rows) == len(doc["trends"]) + 1
    markdown = (tmp_path / "TERRESTRIAL.md").read_text(encoding="utf-8")
    assert "P.1546" in markdown and "ECC T/R 25-08" in markdown and "to be confirmed" in markdown


def test_load_issue_skips_rows_without_required_fields(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text(
        json.dumps(
            {
                "issue": "X",
                "notices": [
                    {
                        "ntc_id": "1",
                        "adm": "EST",
                        "stn_cls": "LM",
                        "freq_min_mhz": 450,
                        "freq_max_mhz": 450.025,
                        "lat": 59.4,
                        "lon": 24.7,
                        "p_erp_kw": 10,
                        "ant_h_m": 30,
                    },
                    {
                        "ntc_id": "2",
                        "adm": "EST",
                        "stn_cls": "LM",
                        "freq_min_mhz": "abc",
                        "lat": 59.4,
                    },
                    {
                        "ntc_id": "3",
                        "adm": "EST",
                        "stn_cls": "LM",
                        "freq_min_mhz": 450,
                        "freq_max_mhz": 450.025,
                        "lon": 24.7,
                    },
                    "not a row",
                ],
            }
        ),
        encoding="utf-8",
    )
    issue = t.load_issue(path)
    assert [n["ntc_id"] for n in issue["notices"]] == ["1"]
    assert issue["skipped_invalid"] == 3


def test_load_issue_rejects_wrong_shape(tmp_path):
    path = tmp_path / "wrong.json"
    path.write_text('{"rows": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="notices"):
        t.load_issue(path)


def test_empty_extract_still_produces_outputs(tmp_path):
    empty = {"issue": "EMPTY", "synthetic": True, "notices": []}
    doc = t.run(empty, empty, REGISTER, tmp_path)
    assert doc["notices"] == [] and doc["trends"] == [] and doc["anomalies"] == []
    assert (tmp_path / "TERRESTRIAL.md").exists()


def test_register_without_frequency_columns_is_rejected(tmp_path):
    path = tmp_path / "register.csv"
    path.write_text("Station number,Class of licence\n1,MVV\n", encoding="utf-8")
    with pytest.raises(ValueError, match="taajuussaraketta"):
        t.register_frequencies(path)


def test_cli_runs_and_fails_cleanly_on_missing_input(tmp_path, capsys):
    prev, curr = json.loads(FIXTURE.read_text(encoding="utf-8"))["issues"]
    for name, issue in (("prev.json", prev), ("curr.json", curr)):
        (tmp_path / name).write_text(json.dumps(issue), encoding="utf-8")
    out = tmp_path / "out"
    code = t.main(
        [
            "--prev",
            str(tmp_path / "prev.json"),
            "--curr",
            str(tmp_path / "curr.json"),
            "--register",
            str(REGISTER),
            "--out",
            str(out),
        ]
    )
    assert code == 0
    assert "3 new, 1 modified, 1 withdrawn" in capsys.readouterr().out
    assert (out / "TERRESTRIAL.md").exists()

    with pytest.raises(SystemExit, match="terrestrial:"):
        t.main(
            [
                "--prev",
                str(tmp_path / "missing.json"),
                "--curr",
                str(tmp_path / "curr.json"),
                "--register",
                str(REGISTER),
                "--out",
                str(out),
            ]
        )


@pytest.mark.data
def test_fixture_bands_overlap_the_real_register(issues, tmp_path):
    # Synteettiset kaistat on valittu niin, että ne osuvat oikeaan rekisteriin.
    freqs = t.register_frequencies(REAL_REGISTER)
    assert len(freqs) > 800 and all(0 < f < 40000 for f in freqs)
    prev, curr = issues
    doc = t.run(prev, curr, REAL_REGISTER, tmp_path)
    assert doc["filter"]["dropped"]["no_band_overlap"] == 0
    assert len(doc["notices"]) == 12

"""The CLI and its output files, on the real BR IFIC MDB."""

import csv
import json
from pathlib import Path

import pytest

from app import pipeline
from app.cards import RESULT_COLUMNS

ROOT = Path(__file__).resolve().parent.parent
SPACE_MDB = ROOT / "data" / "itu-ific-3074" / "ific3074.mdb"
REGISTER = ROOT / "data" / "frequencies_of_interest.csv"
M4 = ROOT / "data" / "taajuusjakotaulukko.json"
TERR_CURR = ROOT / "data" / "itu-terr-ific" / "brific3076.mdb"
TERR_PREV = ROOT / "data" / "itu-terr-ific" / "brific3075.mdb"
OUTPUT_FILES = ("cases.json", "cases.md", "queue.md", "funnel.json", "run.log")

# The real BR IFIC MDBs are never committed: the data tests skip when data/ is missing.
needs_data = pytest.mark.skipif(
    not (SPACE_MDB.is_file() and REGISTER.is_file() and M4.is_file()),
    reason="challenge data missing: run scripts/fetch_data.py",
)
needs_terr = pytest.mark.skipif(
    not (TERR_CURR.is_file() and TERR_PREV.is_file()),
    reason="BR IFIC 3075/3076 MDB missing: run scripts/fetch_data.py",
)


@pytest.fixture(scope="module")
def slice_out(tmp_path_factory) -> Path:
    """One demo-slice run of the real MDB, shared by the output-contract tests."""
    out = tmp_path_factory.mktemp("slice-out")
    assert pipeline.run(SPACE_MDB, REGISTER, M4, out) == 0
    return out


@pytest.mark.data
@needs_data
def test_slice_run_writes_every_output(slice_out):
    for name in OUTPUT_FILES:
        assert (slice_out / name).is_file(), name
    assert (slice_out / "3074_results.csv").is_file()


@pytest.mark.data
@needs_data
def test_slice_run_matches_the_documented_anchors(slice_out):
    """The funnel and the CSV row count the plan fixes."""
    funnel = json.loads((slice_out / "funnel.json").read_text(encoding="utf-8"))
    assert funnel["counts"] == {
        "notices": 196,
        "g1": 41,
        "g2": 19,
        "g3": 18,
        "cannot_decide": 1,
        "exceeds": 9,
        "near": 5,
        "clear": 4,
    }
    assert funnel["queue"] == {"shown": 15}
    assert funnel["mode"] == "slice"
    assert len(funnel["input_sha256"]) == 64
    with (slice_out / "3074_results.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == list(RESULT_COLUMNS)
    assert len(rows) == 196
    assert len(rows[0]) == 19


@pytest.mark.data
@needs_data
def test_slice_cases_json_and_markdown(slice_out):
    cards = json.loads((slice_out / "cases.json").read_text(encoding="utf-8"))
    assert len(cards) == 18
    assert cards[0]["class"] == "exceeds"
    assert "prose" in cards[0]
    assert (slice_out / "cases.md").read_text(encoding="utf-8").startswith("# Cases (18)")
    assert "| 15 |" in (slice_out / "queue.md").read_text(encoding="utf-8")


@pytest.mark.data
@needs_data
def test_run_log_records_the_source_and_the_counts(slice_out):
    log = (slice_out / "run.log").read_text(encoding="utf-8")
    assert "input_sha256=" in log
    assert "ific=3074" in log
    assert "source_file=ific3074.mdb" in log
    assert "g1=41 g2=19 g3=18 cannot_decide=1" in log
    assert "mode=slice" in log


@pytest.mark.data
@needs_data
def test_letters_are_written_for_the_exceeds_cards(slice_out):
    cards = json.loads((slice_out / "cases.json").read_text(encoding="utf-8"))
    exceeds = {card["case_id"] for card in cards if card["class"] == "exceeds"}
    clear = {card["case_id"] for card in cards if card["class"] == "clear"}
    written = {path.stem for path in (slice_out / "letters").iterdir()}
    assert len(exceeds) == 9 and written == exceeds
    assert clear and not written & clear
    assert "letters=9" in (slice_out / "run.log").read_text(encoding="utf-8")


@pytest.mark.data
@needs_data
def test_out_directory_is_created(tmp_path):
    out = tmp_path / "deep" / "nested"
    assert pipeline.run(SPACE_MDB, REGISTER, M4, out, all_bands=True) == 0
    assert (out / "funnel.json").is_file()
    assert json.loads((out / "funnel.json").read_text(encoding="utf-8"))["mode"] == "all"


def test_missing_input_is_a_clear_error(tmp_path):
    from app.ingest import DataError

    with pytest.raises(DataError, match="missing input file"):
        pipeline.run(tmp_path / "nope.mdb", tmp_path / "r.csv", tmp_path / "m4.json")


def test_missing_argument_is_an_argparse_error():
    with pytest.raises(SystemExit) as exit_info:
        pipeline.main(["--ific", "data/itu-ific-3074/ific3074.mdb"])
    assert exit_info.value.code == 2


def test_bad_input_returns_exit_code_two(tmp_path):
    assert (
        pipeline.main(
            [
                "--ific",
                str(tmp_path / "nope.mdb"),
                "--register",
                str(tmp_path / "r.csv"),
                "--m4",
                str(tmp_path / "m4.json"),
                "--out",
                str(tmp_path / "out"),
            ]
        )
        == 2
    )


@pytest.mark.data
@needs_data
def test_missing_limits_is_a_clear_error(tmp_path, capsys):
    """A bad --limits path must print `error: ...` and exit 2, not a traceback."""
    code = pipeline.main(
        [
            "--ific",
            str(SPACE_MDB),
            "--register",
            str(REGISTER),
            "--m4",
            str(M4),
            "--out",
            str(tmp_path / "out"),
            "--limits",
            str(tmp_path / "does-not-exist.csv"),
        ]
    )
    assert code == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.data
@needs_data
def test_register_without_stations_on_a_band_is_a_clear_error(tmp_path):
    """A register that protects nothing must say so instead of producing empty output."""
    from app.ingest import DataError

    empty = tmp_path / "register.csv"
    empty.write_text(
        "Station number,Class of licence,Longitude,Latitude,Channel bandwidth,TX frequency,"
        "RX frequency,Ant gain (dB),Radioation power,Radiation power unit\n"
        "1,BC,24.0,60.0,300.000 kHz,87.9 MHz,87.9 MHz,10,50,W\n",
        encoding="utf-8",
    )
    m4 = tmp_path / "m4.json"
    m4.write_text(
        '{"value": [{"ID": 1, "Sub_band_lower_limit__Hz_": 1000000,'
        ' "Sub_band_upper_limit__Hz_": 2000000, "Services_in_Finnish": ""}]}',
        encoding="utf-8",
    )
    with pytest.raises(DataError, match="no protected band"):
        pipeline.run(SPACE_MDB, empty, m4, tmp_path / "out")


@pytest.mark.data
@needs_data
@needs_terr
def test_one_command_writes_both_space_and_terrestrial_outputs(tmp_path):
    """--terrestrial: the same run writes both output sets into one --out."""
    out = tmp_path / "both"
    assert (
        pipeline.main(
            [
                "--ific",
                str(SPACE_MDB),
                "--register",
                str(REGISTER),
                "--m4",
                str(M4),
                "--terrestrial",
                str(TERR_CURR),
                "--terrestrial-prev",
                str(TERR_PREV),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert (out / "cases.json").is_file()
    assert (out / "terrestrial_findings.json").is_file()
    assert (out / "TERRESTRIAL.md").is_file()
    doc = json.loads((out / "terrestrial_findings.json").read_text(encoding="utf-8"))
    assert len(doc["source"]["sha256"]) == 64
    assert len(doc["audit"]["input_sha256"]) == 64


@pytest.mark.data
@needs_data
def test_without_the_terrestrial_flag_the_space_run_is_unchanged(tmp_path):
    out = tmp_path / "space"
    assert pipeline.run(SPACE_MDB, REGISTER, M4, out) == 0
    assert not (out / "terrestrial_findings.json").exists()
    counts = json.loads((out / "funnel.json").read_text(encoding="utf-8"))["counts"]
    assert (counts["notices"], counts["g1"], counts["g2"]) == (196, 41, 19)
    assert counts["exceeds"] == 9

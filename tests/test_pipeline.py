"""The CLI and its six output files, on the mini package and on the real one."""

import csv
import json
from pathlib import Path

import pytest

from app import pipeline
from app.cards import RESULT_COLUMNS

FIXTURES = Path(__file__).resolve().parent / "fixtures"
OUTPUT_FILES = ("cases.json", "cases.md", "queue.md", "funnel.json", "run.log")


@pytest.fixture(scope="module")
def mini_out(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("mini-out")
    assert (
        pipeline.run(
            FIXTURES / "ific_mini", FIXTURES / "register_mini.csv", FIXTURES / "m4_mini.json", out
        )
        == 0
    )
    return out


def test_mini_run_writes_every_output(mini_out):
    for name in OUTPUT_FILES:
        assert (mini_out / name).is_file(), name
    assert (mini_out / "ific_results.csv").is_file()  # named after the package, not 3074


def test_mini_results_csv_has_one_row_per_notice(mini_out):
    with (mini_out / "ific_results.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == list(RESULT_COLUMNS)
    assert len(rows) == 9
    assert len(rows[0]) == 18


def test_mini_funnel_json_mini_out(mini_out):
    funnel = json.loads((mini_out / "funnel.json").read_text(encoding="utf-8"))
    assert funnel["counts"]["notices"] == 9
    assert funnel["counts"]["g3"] == 2
    assert funnel["queue"]["shown"] == 4
    assert funnel["mode"] == "slice"
    assert len(funnel["input_sha256"]) == 64


def test_mini_cases_json_and_markdown(mini_out):
    cards = json.loads((mini_out / "cases.json").read_text(encoding="utf-8"))
    assert len(cards) == 2
    assert cards[0]["class"] == "exceeds"
    assert "prose" in cards[0]
    assert (mini_out / "cases.md").read_text(encoding="utf-8").startswith("# Cases (2)")
    assert "196" not in (mini_out / "queue.md").read_text(encoding="utf-8")


def test_run_log_records_the_hash_and_the_counts(mini_out):
    log = (mini_out / "run.log").read_text(encoding="utf-8")
    assert "input_sha256=" in log
    assert "ific=ific_mini" in log
    assert "g1=6 g2=4 g3=2 cannot_decide=2" in log
    assert "mode=slice" in log


def test_out_directory_is_created(tmp_path):
    out = tmp_path / "deep" / "nested"
    assert (
        pipeline.run(
            FIXTURES / "ific_mini",
            FIXTURES / "register_mini.csv",
            FIXTURES / "m4_mini.json",
            out,
            all_bands=True,
        )
        == 0
    )
    assert (out / "funnel.json").is_file()
    assert json.loads((out / "funnel.json").read_text(encoding="utf-8"))["mode"] == "all"


def test_missing_input_is_a_clear_error(tmp_path):
    from app.ingest import DataError

    with pytest.raises(DataError, match="missing IFIC directory"):
        pipeline.run(tmp_path / "nope", FIXTURES / "register_mini.csv", FIXTURES / "m4_mini.json")


def test_missing_argument_is_an_argparse_error():
    with pytest.raises(SystemExit) as exit_info:
        pipeline.main(["--ific", "data/itu-ific-3074"])
    assert exit_info.value.code == 2


def test_bad_input_returns_exit_code_two(tmp_path):
    assert (
        pipeline.main(
            [
                "--ific",
                str(tmp_path / "nope"),
                "--register",
                str(FIXTURES / "register_mini.csv"),
                "--m4",
                str(FIXTURES / "m4_mini.json"),
                "--out",
                str(tmp_path / "out"),
            ]
        )
        == 2
    )


def test_missing_limits_is_a_clear_error(tmp_path, capsys):
    """A bad --limits path must print `error: ...` and exit 2, not a traceback."""
    code = pipeline.main(
        [
            "--ific",
            str(FIXTURES / "ific_mini"),
            "--register",
            str(FIXTURES / "register_mini.csv"),
            "--m4",
            str(FIXTURES / "m4_mini.json"),
            "--out",
            str(tmp_path / "out"),
            "--limits",
            str(tmp_path / "does-not-exist.csv"),
        ]
    )
    assert code == 2
    assert "error:" in capsys.readouterr().err


def test_register_without_stations_on_a_band_is_a_clear_error(tmp_path):
    """A register that protects nothing must say so instead of producing empty output."""
    from app.ingest import DataError

    empty = tmp_path / "register.csv"
    empty.write_text(
        "Station number,Class of licence,Longitude,Latitude,Channel bandwidth,TX frequency,"
        "RX frequency,Ant gain (dB),Radioation power,Radiation power unit\n"
        "1,BC,24.0,60.0,300.000 kHz,87.9 MHz,87.9 MHz,10,50,W\n"
    )
    with pytest.raises(DataError, match="no protected band"):
        pipeline.run(FIXTURES / "ific_mini", empty, FIXTURES / "m4_mini.json", tmp_path / "out")


@pytest.mark.data
def test_real_run_writes_the_documented_numbers(challenge, tmp_path):
    out = tmp_path / "real"
    assert (
        pipeline.run(
            Path(__file__).resolve().parent.parent / "data" / "itu-ific-3074",
            Path(__file__).resolve().parent.parent / "data" / "frequencies_of_interest.csv",
            Path(__file__).resolve().parent.parent / "data" / "taajuusjakotaulukko.json",
            out,
        )
        == 0
    )
    for name in OUTPUT_FILES:
        assert (out / name).is_file(), name
    with (out / "3074_results.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 196
    cards = json.loads((out / "cases.json").read_text(encoding="utf-8"))
    assert len(cards) == 18
    funnel = json.loads((out / "funnel.json").read_text(encoding="utf-8"))
    assert funnel["counts"]["exceeds"] == 9
    assert funnel["queue"] == {"shown": 15}
    assert challenge.slice.result.counts["g3"] == len(cards)

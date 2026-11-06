"""Ingest: unit normalisation, the register, the IFIC tables and the error paths."""

from pathlib import Path

import pytest

from app import ingest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("3 520.500 MHz", 3520.5),
        ("300k", 0.3),
        ("0,1G", 100.0),
        ("1.5 GHz", 1500.0),
        ("148.500 MHz", 148.5),
        ("", None),
        (None, None),
        ("abc", None),
        ("  12.5MHz ", 12.5),
    ],
)
def test_mhz_normalises_units(raw, expected):
    assert ingest.mhz(raw) == expected


def test_watts_converts_units():
    assert ingest.watts("145", "W") == 145.0
    assert ingest.watts("2", "kW") == 2000.0
    assert ingest.watts("500", "mW") == 0.5
    assert ingest.watts("", "W") is None
    assert ingest.watts(None, None) is None


def test_load_register_skips_rows_without_frequency():
    stations, counts = ingest.load_register(FIXTURES / "register_mini.csv")
    assert counts == {"rows": 9, "stations": 8, "skipped_no_freq": 1}
    by_id = {s.id: s for s in stations}
    assert "900100006" not in by_id  # neither RX nor TX
    assert by_id["900100001"].gain_db == 40.0
    assert by_id["900100001"].power_w == 145.0
    assert by_id["900100003"].gain_db is None  # register row without a gain
    assert by_id["900100004"].power_w is None  # register row without a power


def test_station_uses_tx_when_rx_is_missing():
    stations, _ = ingest.load_register(FIXTURES / "register_mini.csv")
    station = next(s for s in stations if s.id == "900100005")
    assert station.rx_mhz is None
    assert station.centre_mhz == 3560.0
    assert (station.lo_mhz, station.hi_mhz) == (3510.0, 3610.0)


def test_empty_file_is_a_clear_error(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    with pytest.raises(ingest.DataError, match="empty file"):
        ingest.rows(empty)


def test_missing_column_names_the_column(tmp_path):
    bad = tmp_path / "register.csv"
    bad.write_text("Station number,Latitude\n1,60\n")
    with pytest.raises(ingest.DataError, match="missing column"):
        ingest.load_register(bad)


def test_header_only_file_is_a_clear_error(tmp_path):
    header_only = tmp_path / "only.csv"
    header_only.write_text("a,b\n")
    with pytest.raises(ingest.DataError, match="no data rows"):
        ingest.rows(header_only)


def test_missing_ific_directory_is_a_clear_error(tmp_path):
    with pytest.raises(ingest.DataError, match="missing IFIC directory"):
        ingest.load_ific(tmp_path / "nope")


def test_missing_required_table_is_a_clear_error(tmp_path):
    (tmp_path / "ific" / "csv").mkdir(parents=True)
    (tmp_path / "ific" / "csv" / "notice.csv").write_text(
        "ntc_id,adm,ntc_type,act_code\n1,TST,G,A\n"
    )
    with pytest.raises(ingest.DataError, match="freq.csv"):
        ingest.load_ific(tmp_path / "ific")


def test_m4_without_value_array_is_a_clear_error(tmp_path):
    bad = tmp_path / "m4.json"
    bad.write_text('{"error": "nope"}')
    with pytest.raises(ingest.DataError, match="value"):
        ingest.load_m4(bad)


def test_load_ific_mini_counts():
    ific = ingest.load_ific(FIXTURES / "ific_mini")
    assert ific.counts["notice"] == 9
    assert ific.counts["freq"] == 10
    assert ific.counts["s_beam"] == 7
    assert ific.counts["geo"] == 3
    assert ific.counts["orbit"] == 2
    assert len(ific.input_sha256) == 64
    assert ific.file.endswith(".zip")  # the mini package has no mdb


@pytest.mark.data
def test_real_package_row_counts(challenge):
    counts = challenge.slice.ific.counts
    assert counts["notice"] == 196
    assert counts["freq"] == 95865
    assert counts["grp"] == 34365
    assert counts["emiss"] == 216455
    assert counts["s_beam"] == 2304
    assert counts["geo"] == 72
    assert counts["non_geo"] == 112
    assert counts["orbit"] == 11221


@pytest.mark.data
def test_real_register_and_hash(challenge):
    assert challenge.slice.counts == {"rows": 874, "stations": 871, "skipped_no_freq": 3}
    assert challenge.slice.ific.input_sha256 == challenge.all.ific.input_sha256
    assert len(challenge.slice.ific.input_sha256) == 64

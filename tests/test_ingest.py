"""Ingest: unit normalisation, the register, the IFIC tables and the error paths."""

import tracemalloc
from datetime import date
from pathlib import Path

import pytest

from app import ingest

ROOT = Path(__file__).resolve().parent.parent
MDB = ROOT / "data" / "itu-ific-3074" / "ific3074.mdb"
REGISTER = ROOT / "data" / "frequencies_of_interest.csv"

# The register columns load_register reads, in the order the real CSV carries them.
REGISTER_HEADER = (
    "Station number,Class of licence,Latitude,Longitude,Channel bandwidth,TX frequency,"
    "RX frequency,Ant gain (dB),Radioation power,Radiation power unit\n"
)


def _register(path: Path, *rows: str) -> Path:
    path.write_text(REGISTER_HEADER + "".join(f"{row}\n" for row in rows), encoding="utf-8")
    return path


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


def test_deadline_reads_the_exported_date():
    """grp_res35.d_ms_next_deadline is rendered MM/DD/YY; anything else stays None."""
    assert ingest.deadline("12/19/26 00:00:00") == date(2026, 12, 19)
    assert ingest.deadline("01/19/31 00:00:00") == date(2031, 1, 19)
    assert ingest.deadline("12/18/19 00:00:00") == date(2019, 12, 18)
    assert ingest.deadline("") is None
    assert ingest.deadline(None) is None
    assert ingest.deadline("not a date") is None


def test_load_register_skips_rows_without_frequency(tmp_path):
    path = _register(
        tmp_path / "register.csv",
        "1,MVV,60.0,24.0,300.000 kHz,87.9 MHz,87.9 MHz,40,145,W",  # kept
        "2,MVV,60.0,24.0,300.000 kHz,,,10,50,W",  # neither RX nor TX
        "3,MVV,60.0,24.0,300.000 kHz,87.9 MHz,87.9 MHz,,50,W",  # gain missing
        "4,MVV,60.0,24.0,300.000 kHz,87.9 MHz,87.9 MHz,10,,W",  # power missing
    )
    stations, counts = ingest.load_register(path)
    assert counts == {"rows": 4, "stations": 3, "skipped_no_freq": 1}
    by_id = {s.id: s for s in stations}
    assert "2" not in by_id
    assert by_id["1"].gain_db == 40.0
    assert by_id["1"].power_w == 145.0
    assert by_id["3"].gain_db is None
    assert by_id["4"].power_w is None


def test_station_uses_tx_when_rx_is_missing(tmp_path):
    path = _register(tmp_path / "register.csv", "5,MVV,60.0,24.0,100.000 MHz,3560.0 MHz,,10,50,W")
    stations, _ = ingest.load_register(path)
    station = stations[0]
    assert station.rx_mhz is None
    assert station.centre_mhz == 3560.0
    assert (station.lo_mhz, station.hi_mhz) == (3510.0, 3610.0)


def test_bandwidth_is_the_smaller_of_channel_and_transmission(tmp_path):
    """Traficom: when the two disagree, the smaller one is what the register means."""
    path = tmp_path / "register.csv"
    path.write_text(
        "Station number,Class of licence,Latitude,Longitude,Channel bandwidth,"
        "Transmission bandwidth,TX frequency,RX frequency,Ant gain (dB)\n"
        "1,MVV,60.0,24.0,118600k,2500.000 kHz,3726.8 MHz,3726.8 MHz,40\n"
        "2,MVV,60.0,24.0,,300.000 kHz,87.9 MHz,87.9 MHz,40\n",
        encoding="utf-8",
    )
    stations, _ = ingest.load_register(path)
    assert stations[0].bw_mhz == pytest.approx(2.5)  # 118,6 MHz is the data-entry artefact
    assert stations[1].bw_mhz == pytest.approx(0.3)  # only one column carries a value


def test_load_register_keeps_only_the_bands_asked_for(tmp_path):
    """The band filter drops the rows no gate can use, and the skip counters still count them."""
    path = _register(
        tmp_path / "register.csv",
        "1,MVV,60.0,24.0,100.000 MHz,3600.0 MHz,3600.0 MHz,10,50,W",  # on the slice
        "2,MVV,60.0,24.0,100.000 MHz,100.0 MHz,100.0 MHz,10,50,W",  # far below it
        "3,MVV,60.0,24.0,100.000 MHz,,,10,50,W",  # no frequency
        "4,MVV,,,100.000 MHz,100.0 MHz,100.0 MHz,10,50,W",  # no position
    )
    stations, counts = ingest.load_register(path, ((3470.0, 3780.0),))
    assert [s.id for s in stations] == ["1"]
    assert counts == {
        "rows": 4,
        "stations": 1,
        "skipped_no_freq": 1,
        "skipped_no_position": 1,
    }


def test_register_streams_a_million_rows(tmp_path):
    """1 M rows: only the in-band stations are kept and the file is never held as a list."""
    path = tmp_path / "big.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(REGISTER_HEADER)
        for i in range(1_000_000):
            freq = "3 600.000 MHz" if i % 1000 == 0 else "100.000 MHz"
            handle.write(f"{i},MVV,60.0,24.0,100.000 MHz,{freq},{freq},10,50,W\n")
    tracemalloc.start()
    stations, counts = ingest.load_register(path, ((3470.0, 3780.0),))
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert counts["rows"] == 1_000_000
    assert counts["stations"] == 1000
    # The whole file as a list of dicts is ~1 GB; streaming keeps the peak under 20 MB.
    assert peak < 20 * 1024 * 1024


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


def test_missing_mdb_is_a_clear_error(tmp_path):
    with pytest.raises(ingest.DataError, match="missing input file"):
        ingest.load_ific(tmp_path / "nope.mdb")


def test_missing_mdb_export_is_a_clear_error(tmp_path, monkeypatch):
    mdb = tmp_path / "x.mdb"
    mdb.write_bytes(b"not an Access database")
    monkeypatch.setattr(ingest.shutil, "which", lambda name: None)
    with pytest.raises(ingest.DataError, match="mdb-export"):
        ingest.load_ific(mdb)


# The missing-table wording only appears once mdb-export runs against the file.
# Without mdbtools the clear error is the install hint, which the test above covers.
needs_mdbtools = pytest.mark.skipif(
    ingest.shutil.which("mdb-export") is None,
    reason="mdbtools not installed: the table-name error needs mdb-export",
)


@needs_mdbtools
def test_unreadable_table_is_a_clear_error(tmp_path):
    """A file that is not an Access database: the first required table names itself."""
    mdb = tmp_path / "fake.mdb"
    mdb.write_bytes(b"not an Access database")
    with pytest.raises(ingest.DataError, match="notice"):
        ingest.load_ific(mdb)


def test_exported_rows_are_mapped_to_ific_data(tmp_path, monkeypatch):
    """load_ific is a mapping over the exported rows; mdb-export itself is the tested shell-out."""
    mdb = tmp_path / "ific3074.mdb"
    mdb.write_bytes(b"x")
    tables = {
        "notice": [
            {
                "ntc_id": "1",
                "adm": "CHN ",
                "ntc_type": "N",
                "act_code": "A",
                "prov": "11.2",
                "ntwk_org": "ORG",
                "adm_ref_id": "REF",
                "tgt_ntc_id": "2",
            }
        ],
        "freq": [
            {
                "ntc_id": "1",
                "beam_name": "CDN",
                "grp_id": "9",
                "emi_rcp": "E",
                "freq_min": "3 642 MHz",
                "freq_max": "3 678 MHz",
            },
            {"ntc_id": "1", "emi_rcp": "E", "freq_min": "", "freq_max": ""},  # unusable
        ],
        "s_beam": [
            {
                "ntc_id": "1",
                "beam_name": "CDN",
                "gain": "28.5",
                "freq_min": "3642",
                "freq_max": "3678",
            }
        ],
        "emiss": [{"grp_id": "9", "pwr_ds_max": "-50.0"}],
        "geo": [{"ntc_id": "1", "sat_name": "COMPASS-80E", "long_nom": "80"}],
        "orbit": [{"ntc_id": "1", "apog_km": "35786", "perig_km": "35786", "inclin_ang": "0"}],
        "pub_ssn": [
            {
                "ntc_id": "1",
                "seq_no": "1",
                "ssn_ref": "CR/D",
                "ssn_no": "5378",
                "ssn_rev": "",
                "ssn_rev_no": "",
            },
            {
                "ntc_id": "1",
                "seq_no": "2",
                "ssn_ref": "CR/C",
                "ssn_no": "6324",
                "ssn_rev": "M",
                "ssn_rev_no": "1",
            },
        ],
    }
    monkeypatch.setattr(ingest, "_export", lambda path, table: tables.get(table, []))
    ific = ingest.load_ific(mdb)
    assert ific.counts["notice"] == 1
    assert ific.counts["freq"] == 1  # the row without a frequency is dropped
    assert ific.counts["s_beam"] == 1
    assert ific.counts["orbit"] == 1
    assert ific.counts["grp"] == 0  # an absent optional table is not an error
    assert ific.counts["grp_res35"] == 0
    assert ific.counts["pub_ssn"] == 2
    assert ific.publications["1"] == [
        ingest.Publication("1", "1", "CR/D", "5378", "", ""),
        ingest.Publication("1", "2", "CR/C", "6324", "M", "1"),
    ]
    assert ific.notices["1"].pub_refs == ("CR/D", "CR/C")
    assert ific.res35 == {}  # an absent grp_res35 leaves every notice without a deadline
    assert ific.notices["1"].adm == "CHN"
    assert ific.notices["1"].tgt_ntc_id == "2"
    assert ific.geo["1"].sat_name == "COMPASS-80E"
    beam = ific.beam("1", "CDN")
    assert beam is not None and beam.gain_db == 28.5
    assert ific.emiss["9"] == -50.0
    assert ific.file == "ific3074.mdb"
    assert len(ific.input_sha256) == 64


def test_ntc_lnk_maps_a_filing_to_the_notice_it_follows(tmp_path, monkeypatch):
    """ntc_lnk rows become `links`; a row without a target is not a link."""
    mdb = tmp_path / "ific3074.mdb"
    mdb.write_bytes(b"x")
    tables = {
        "notice": [{"ntc_id": "1", "adm": "CHN", "ntc_type": "G", "act_code": "M"}],
        "freq": [
            {
                "ntc_id": "1",
                "emi_rcp": "E",
                "freq_min": "3 600 MHz",
                "freq_max": "3 610 MHz",
            }
        ],
        "ntc_lnk": [
            {"ntc_id": "1", "lnk_ntc_id": "100543885", "ntf_rsn": "N", "lnkntf_rsn": "A"},
            {"ntc_id": "1", "lnk_ntc_id": "", "ntf_rsn": "N", "lnkntf_rsn": "A"},
        ],
    }
    monkeypatch.setattr(ingest, "_export", lambda path, table: tables.get(table, []))
    ific = ingest.load_ific(mdb)
    assert ific.links == {"1": [ingest.Link(ntc_id="100543885", reason="A")]}
    assert ific.notices["1"].act_code == "M"
    assert ific.counts["ntc_lnk"] == 2  # the raw rows; only one of them is a link


@pytest.mark.data
def test_real_mdb_row_counts(challenge):
    counts = challenge.slice.ific.counts
    assert counts["notice"] == 196
    assert counts["freq"] == 95865
    assert counts["grp"] == 34365
    assert counts["emiss"] == 216455
    assert counts["s_beam"] == 2304
    assert counts["geo"] == 72
    assert counts["non_geo"] == 112
    assert counts["orbit"] == 11221
    assert counts["grp_res35"] == 254
    assert counts["pub_ssn"] == 225


@pytest.mark.data
def test_real_publication_parts(challenge):
    """pub_ssn names the exact BR IFIC part; a notification has no pub_ssn row."""
    assert challenge.slice.ific.notices["124520183"].pub_refs == ("CR/D", "CR/C")
    assert challenge.slice.ific.notices["124545403"].pub_refs == ("API/B", "API/A")
    assert challenge.slice.ific.notices["103500417"].pub_refs == ()


@pytest.mark.data
def test_real_register_and_mdb_hash(challenge):
    assert challenge.slice.counts == {"rows": 874, "stations": 871, "skipped_no_freq": 3}
    assert challenge.slice.ific.file == "ific3074.mdb"
    assert challenge.slice.ific.input_sha256 == challenge.all.ific.input_sha256
    assert challenge.slice.ific.input_sha256 == ingest.sha256(MDB)
    assert len(challenge.slice.ific.input_sha256) == 64


@pytest.mark.data
def test_real_register_keeps_rows_without_a_licence_class():
    """294 rows carry no Class of licence; none is dropped and no class is guessed."""
    stations, _ = ingest.load_register(REGISTER)
    assert sum(1 for station in stations if not station.licence) == 294

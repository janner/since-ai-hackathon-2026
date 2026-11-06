import openpyxl
import pytest

from scripts import fetch_data


def test_html_instead_of_zip_is_rejected():
    with pytest.raises(SystemExit):
        fetch_data.check_zip(b"<!DOCTYPE html><html>...")
    assert fetch_data.check_zip(b"PK\x03\x04rest") == b"PK\x03\x04rest"


def test_xlsx_rows_skips_preamble_and_finnish_header(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Traficom / Since AI Hackathon 6.-8.11.2026"])
    ws.append([None, None, "WGS84"])
    ws.append(["Station number", "Class of licence", "RX frequency", None])
    ws.append(["Asemanro", "Lupalaji", "RX-taajuus", None])
    ws.append([983816, "MVV", "3726.8 MHz", None])
    ws.append([None, None, None, None])
    p = tmp_path / "f.xlsx"
    wb.save(p)
    assert list(fetch_data.xlsx_rows(p)) == [
        ["Station number", "Class of licence", "RX frequency"],
        [983816, "MVV", "3726.8 MHz"],
    ]

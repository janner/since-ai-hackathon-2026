"""The numeric guard: a sentence may only repeat numbers the card already has."""

from app import guard


def _card() -> dict:
    return {
        "case_id": "3074-103500417",
        "class": "exceeds",
        "band": {"freq_min_mhz": 3662.0, "freq_max_mhz": 3698.0},
        "calculation": {"margin_db": 3.24, "pfd_dbw_m2_hz": -184.78, "limit_dbw_m2_hz": -188.02},
    }


def test_scan_normalises_decimals_and_thousands():
    assert guard.scan("3 662-3 698 MHz") == [("3662", 3662.0), ("3698", 3698.0)]
    assert guard.scan("marginaali +3,24 dB") == [("+3,24", 3.24)]
    assert guard.scan("−184,78 dB(W/m²/Hz)") == [("−184,78", -184.78)]


def test_card_numbers_are_accepted():
    text = "PFD -184,78 dB(W/m²/Hz), raja -188,02, marginaali +3,24 dB, kaista 3 662-3 698 MHz."
    assert guard.check(text, _card()) == []


def test_invented_number_is_rejected():
    assert guard.check("marginaali +9,99 dB", _card()) == ["+9,99"]


def test_flipped_sign_is_rejected():
    assert guard.check("marginaali -3,24 dB", _card()) == ["-3,24"]
    assert guard.check("PFD 184,78 dB(W/m²/Hz)", _card()) == ["184,78"]


def test_case_id_is_not_an_invented_number():
    assert guard.check("Tapaus 3074-103500417 on tarkistettava.", _card()) == []


def test_unit_names_are_not_numbers():
    assert guard.check("dB(W/m²/Hz) on suure, ei luku.", _card()) == []


def test_empty_text_is_accepted():
    assert guard.check("", _card()) == []

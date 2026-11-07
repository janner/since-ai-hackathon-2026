"""The feedback form's parsing and storage text, without starting the server."""

from scripts.feedback_server import entry_from, markdown


def test_feedback_needs_words():
    entry, error = entry_from({"feedback": [""], "missing": [""]})
    assert entry is None
    assert error


def test_feedback_rejects_bad_rating():
    entry, error = entry_from({"feedback": ["Toimii."], "useful": ["9"]})
    assert entry is None
    assert error


def test_feedback_entry_and_markdown():
    entry, error = entry_from(
        {
            "name": ["Testi Asiakas"],
            "feedback": ["Lomake toimii."],
            "useful": ["5"],
            "understood": ["kylla"],
            "pilot": ["ehka"],
            "language": ["suomi"],
            "t2_card": ["Kortti kertoo, että keilan geometria puuttuu."],
            "t3_next": ["Kopioi kysymyksen ja lähettää sen."],
            "baseline": ["Yksi henkilö hakee IFIC:n ja käy sen läpi päivässä."],
            "trust": ["4"],
            "does_not": ["Ei kerro keilan geometriaa."],
            "contact_ok": ["yes"],
            "contact": ["testi@example.invalid"],
        }
    )
    assert error is None
    assert entry is not None
    assert entry["id"]
    assert entry["contact_ok"] == "yes"
    text = markdown(entry)
    assert "Lomake toimii." in text
    assert "5/5" in text
    assert "Kyllä" in text
    assert "Ehkä" in text
    assert "Suomi" in text
    assert "Tehtävä 2: tapaus" in text
    assert "Tausta: nykytila" in text
    assert "4/5" in text
    assert "Ei kerro keilan geometriaa." in text

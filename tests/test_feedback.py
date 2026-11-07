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

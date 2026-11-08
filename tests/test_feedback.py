"""The feedback form's parsing and storage text, without starting the server."""

from scripts.feedback_server import entry_from, markdown


def test_feedback_needs_words():
    entry, error = entry_from({"feedback": [""], "missing": [""]})
    assert entry is None
    assert error


def test_feedback_rejects_bad_rating():
    entry, error = entry_from({"feedback": ["Works."], "useful": ["9"]})
    assert entry is None
    assert error


def test_feedback_entry_and_markdown():
    entry, error = entry_from(
        {
            "name": ["Test Customer"],
            "feedback": ["The form works."],
            "useful": ["5"],
            "understood": ["kylla"],
            "pilot": ["ehka"],
            "language": ["suomi"],
            "t2_card": ["The card says the beam geometry is missing."],
            "t3_next": ["Copy the question and send it."],
            "baseline": ["One person fetches the IFIC and goes through it in a day."],
            "trust": ["4"],
            "does_not": ["It does not show the beam geometry."],
            "contact_ok": ["yes"],
            "contact": ["testi@example.invalid"],
        }
    )
    assert error is None
    assert entry is not None
    assert entry["id"]
    assert entry["contact_ok"] == "yes"
    text = markdown(entry)
    assert "The form works." in text
    assert "5/5" in text
    assert "Yes" in text
    assert "Maybe" in text
    assert "Finnish" in text
    assert "Task 2: the case" in text
    assert "Background: how it is done today" in text
    assert "4/5" in text
    assert "It does not show the beam geometry." in text

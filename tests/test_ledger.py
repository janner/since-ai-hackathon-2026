"""The complaint ledger and its statistics: no data files needed, one small fixture each."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import ledger, main, stats


def ev(complaint_id, type_, at, **payload):
    return ledger.event(complaint_id, type_, at, "spec-01", payload)


def history(open_at="2023-01-10T09:00:00+02:00", closed_after=20, outcome="filing_modified"):
    """One complaint: opened, a letter, a reply, and the closing decision."""
    start = datetime.fromisoformat(open_at)
    letter_at = (start + timedelta(days=2)).isoformat()
    reply = (start + timedelta(days=closed_after)).isoformat()
    end = (start + timedelta(days=closed_after + 5)).isoformat()
    return [
        ev(
            "C-1",
            "opened",
            open_at,
            issue_type="pfd_exceedance",
            adm="CHN",
            sat_name="SYN-ATLAS-3",
            band={"freq_min_mhz": 3440.0, "freq_max_mhz": 3480.0},
            **{"class": "exceeds"},
        ),
        ev("C-1", "letter_sent", letter_at, action="comment_sent", letter="out/letters/C-1.md"),
        ev("C-1", "reply_received", reply),
        ev("C-1", "closed", end, outcome=outcome),
    ]


def test_closed_lists_reject_anything_else():
    with pytest.raises(ValueError, match="unknown event type"):
        ev("C-1", "phoned", "2023-01-10T09:00:00+02:00")
    with pytest.raises(ValueError, match="unknown issue_type"):
        ev("C-1", "opened", "2023-01-10T09:00:00+02:00", issue_type="vibes")
    with pytest.raises(ValueError, match="unknown outcome"):
        ev("C-1", "closed", "2023-01-10T09:00:00+02:00", outcome="happy")
    # A complaint cannot be closed as pending: that is what an open one looks like.
    with pytest.raises(ValueError, match="not 'pending'"):
        ev("C-1", "closed", "2023-01-10T09:00:00+02:00", outcome="pending")


def test_the_state_is_folded_from_the_events(tmp_path):
    ledger.append(history(), directory=tmp_path)
    (complaint,) = ledger.complaints(ledger.read(directory=tmp_path))
    assert complaint["status"] == "closed"
    assert complaint["outcome"] == "filing_modified"
    assert complaint["actions"] == ["comment_sent"]
    assert complaint["letters"] == ["out/letters/C-1.md"]
    # Letters go out two days after the opening, so the reply is 18 days after the letter.
    assert complaint["days_to_reply"] == 18


def test_a_reopened_complaint_is_open_again(tmp_path):
    events = history()
    end = (datetime.fromisoformat(events[-1]["at"]) + timedelta(days=1)).isoformat()
    events.append(ev("C-1", "reopened", end))
    ledger.append(events, directory=tmp_path)
    (complaint,) = ledger.complaints(ledger.read(directory=tmp_path))
    assert complaint["status"] == "open"


def test_a_second_notice_of_the_same_case_opens_no_second_complaint(tmp_path):
    events = [*history(), *history(open_at="2026-11-07T18:00:00+02:00")]
    ledger.append(events, directory=tmp_path)
    folded = ledger.read(directory=tmp_path)
    assert len(ledger.complaints(folded)) == 1
    assert ledger.open_complaint(folded, "C-1") is None  # it is closed
    assert ledger.open_complaint(folded, "other") is None


def test_statistics_answer_the_three_questions(tmp_path):
    ledger.append(history(closed_after=10), directory=tmp_path)
    ledger.append(
        [*history(open_at="2024-03-01T09:00:00+02:00", closed_after=30)][1:],
        directory=tmp_path,
    )
    summary, items = stats.report(directory=tmp_path, synthetic=False)
    assert summary["totals"]["complaints"] == 1  # the second group has no `opened` line
    assert summary["admins"][0]["key"] == "CHN"
    assert summary["admins"][0]["count"] == 1
    assert summary["actions"][0]["key"] == "comment_sent"
    assert summary["trend"][0]["year"] == "2023"
    assert summary["totals"]["median_days"] == 8


def test_the_api_refuses_a_loose_event(tmp_path, monkeypatch):
    monkeypatch.setenv("KAISTA_LEDGER", str(tmp_path))
    ledger.append(history(), directory=tmp_path)
    client = TestClient(main.app)
    assert client.get("/api/stats").json()["totals"]["complaints"] == 1
    closed_as_pending = {"type": "closed", "payload": {"outcome": "pending"}}
    bad = client.post("/api/complaints/C-1/events", json=closed_as_pending)
    assert bad.status_code == 422
    no_reply = {"type": "closed", "payload": {"outcome": "no_reply"}}
    missing = client.post("/api/complaints/nope/events", json=no_reply)
    assert missing.status_code == 404


def test_the_api_lists_the_complaints_for_a_card(tmp_path, monkeypatch):
    """The card's history fetch: same administration or network, with the reply note."""
    monkeypatch.setenv("KAISTA_LEDGER", str(tmp_path))
    events = history()
    events[2] = ev("C-1", "reply_received", events[2]["at"], note="we will coordinate")
    ledger.append(events, directory=tmp_path)
    client = TestClient(main.app)
    rows = client.get("/api/complaints?adm=CHN&sat_name=SYN-ATLAS-3").json()
    assert len(rows) == 1
    assert rows[0]["complaint_id"] == "C-1"
    assert rows[0]["status"] == "closed"
    assert rows[0]["events"][2]["payload"]["note"] == "we will coordinate"
    assert client.get("/api/complaints?adm=USA").json() == []

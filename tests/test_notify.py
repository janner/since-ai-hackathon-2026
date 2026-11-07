"""The Teams digest: the numbers, the top three, the empty case, the delivery path."""

import json

from scripts import notify


def make_case(ntc_id, klass, provision, margin, ific="3074"):
    return {
        "case_id": f"{ific}-{ntc_id}",
        "class": klass,
        "regulatory_stage": {"provision": provision, "label": "", "source": ""},
        "calculation": {"margin_db": margin},
        "source": {"ific": ific, "keys": {"ntc_id": ntc_id}},
    }


def write_out(tmp_path, counts, cases):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "funnel.json").write_text(json.dumps({"counts": counts}), encoding="utf-8")
    (tmp_path / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
    return tmp_path


COUNTS = {
    "notices": 196,
    "g1": 41,
    "g2": 19,
    "g3": 18,
    "cannot_decide": 1,
    "exceeds": 9,
    "near": 5,
    "not_space": 2,
    "clear": 4,
}


def test_message_carries_numbers_and_link(tmp_path):
    out = write_out(tmp_path, COUNTS, [make_case("124545403", "exceeds", "No. 9.1", 60.44)])
    counts, cases = notify.load(out)
    message = notify.build_message(counts, notify.top_cases(cases), "3074", "http://kaista.test")
    assert "196 → 41 → 19 → 18 + 1" in message
    assert "9 ylittää · 5 lähellä" in message
    assert "17 huomioitavaa" in message
    assert "http://kaista.test" in message
    assert "60,44 dB" in message  # Finnish decimal comma


def test_top_three_is_queue_order_not_margin(tmp_path):
    cases = [
        make_case("A", "exceeds", "No. 11.2", 99.0),  # biggest margin, but recorded in the MIFR
        make_case("B", "exceeds", "No. 9.6", 2.0),  # can still be influenced: ranks first
        make_case("C", "exceeds", "No. 9.6", 1.0),
        make_case("D", "exceeds", "No. 9.1", 0.5),  # same rank as B, smaller margin
        make_case("E", "near", "No. 9.6", -0.5),  # another class, last
        make_case("F", "clear", "No. 9.6", -9.0),  # never queued
    ]
    # Rank 0 (9.6/9.1) sorts by margin desc: B(2.0), C(1.0), D(0.5) -> ["B", "C", "D"].
    top = notify.top_cases(cases)
    assert [case["source"]["keys"]["ntc_id"] for case in top] == ["B", "C", "D"]
    assert top[0]["calculation"]["margin_db"] == 2.0


def test_zero_cases_gets_the_short_message():
    counts = dict(COUNTS, exceeds=0, near=0, not_space=0, cannot_decide=0)
    message = notify.build_message(counts, [], "3074", "http://kaista.test")
    assert message == notify.EMPTY_MESSAGE
    card = notify.build_card(counts, [], "3074", "http://kaista.test")
    assert card["attachments"][0]["content"]["body"][0]["text"] == notify.EMPTY_MESSAGE


def test_dry_run_writes_markdown_json_and_html(tmp_path):
    write_out(tmp_path, COUNTS, [make_case("124545403", "exceeds", "No. 9.1", 60.44)])
    assert notify.main(["--dry-run", "--html", "--out", str(tmp_path)]) == 0
    markdown = (tmp_path / "teams_message.md").read_text(encoding="utf-8")
    assert "124545403" in markdown
    card_text = (tmp_path / "teams_message.json").read_text(encoding="utf-8")
    assert json.loads(card_text)
    assert "application/vnd.microsoft.card.adaptive" in card_text
    page = (tmp_path / "teams_message.html").read_text(encoding="utf-8")
    assert page.startswith("<!DOCTYPE html>")
    assert "BR IFIC 3074" in page
    assert "Kiireellisimmät" in page


def test_html_preview_renders_headings_bold():
    page = notify.build_html("# Otsikko\n\nrivi", "3074", "http://kaista.test")
    assert "<p><b>Otsikko</b></p>" in page
    assert "<p>rivi</p>" in page


def test_send_without_webhook_fails_cleanly(tmp_path, monkeypatch, capsys):
    write_out(tmp_path, COUNTS, [make_case("124545403", "exceeds", "No. 9.1", 60.44)])
    monkeypatch.delenv("TEAMS_WEBHOOK_URL", raising=False)
    assert notify.main(["--send", "--out", str(tmp_path)]) == 1
    assert "TEAMS_WEBHOOK_URL puuttuu" in capsys.readouterr().err


def test_send_posts_the_card_to_the_webhook(tmp_path, monkeypatch):
    write_out(tmp_path, COUNTS, [make_case("124545403", "exceeds", "No. 9.1", 60.44)])
    monkeypatch.setenv("TEAMS_WEBHOOK_URL", "https://example.invalid/webhook")
    posted = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout=None):
        posted["url"] = request.full_url
        posted["body"] = json.loads(request.data)
        posted["content_type"] = request.headers["Content-type"]
        return Response()

    monkeypatch.setattr(notify.urllib.request, "urlopen", fake_urlopen)
    assert notify.main(["--send", "--out", str(tmp_path)]) == 0
    assert posted["url"] == "https://example.invalid/webhook"
    assert posted["content_type"] == "application/json"
    assert posted["body"]["attachments"][0]["content"]["type"] == "AdaptiveCard"

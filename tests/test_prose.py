"""Prose: the LLM is optional, the template is the floor, the guard is the referee."""

import pytest

from app import prose

CARD = {
    "case_id": "3074-103500417",
    "class": "exceeds",
    "band": {"freq_min_mhz": 3662.0, "freq_max_mhz": 3698.0},
    "coverage": {"sat_name": "COMPASS-80E", "beam": "CDN", "elevation_deg": 4.85},
    "parties": {"admin": "CHN"},
    "victim": {"station": "983816"},
    "calculation": {
        "pfd_dbw_m2_hz": -184.78,
        "limit_dbw_m2_hz": -188.02,
        "margin_db": 3.24,
    },
    "m4": {"services_in_finland": "MOBILE AND FIXED", "satellite_use": False},
    "next_action": {
        "question": (
            "Can China confirm the worst-case PFD the COMPASS-80E CDN beam produces on "
            "Finnish territory in the 3 662-3 698 MHz range?"
        )
    },
}


@pytest.fixture(autouse=True)
def _no_llm_endpoint(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)


def test_without_an_endpoint_the_template_is_used():
    draft = prose.draft_summary(CARD)
    assert draft["source"] == "template"
    assert "3074-103500417" in draft["text"]
    assert "-184,78" in draft["text"]
    assert "(no satellite downlink allocation)" in draft["text"]
    assert "no satellite downlink allocation on" not in draft["text"]


def test_a_partial_m4_gap_names_the_gap():
    """A mixed band says which part has no satellite service, not that the whole band has none."""
    card = {
        **CARD,
        "m4": {
            "services_in_finland": "FIXED SATELLITE (SPACE-TO-EARTH), MOBILE AND FIXED",
            "satellite_use": False,
            "gaps": [[3600.0, 3800.0]],
        },
    }
    text = prose.draft_summary(card)["text"]
    assert "no satellite downlink allocation on 3\u00a0600-3\u00a0800 MHz" in text


def test_letter_template_asks_the_question():
    draft = prose.draft_letter(CARD)
    assert draft["source"] == "template"
    assert CARD["next_action"]["question"] in draft["text"]


def test_a_beam_card_asks_the_worst_case_not_the_service_area():
    # Traficom Q&A Q3: beams are not relevant, the worst case is always assumed.
    question = CARD["next_action"]["question"]
    letter = prose.draft_letter(CARD)["text"]
    assert "service area" not in question and "worst" in question
    assert "service area" not in letter and "worst" in letter


def test_a_failing_llm_falls_back_to_the_template():
    def broken_chat(messages):
        raise TimeoutError("endpoint down")

    draft = prose.draft_summary(CARD, chat=broken_chat)
    assert draft["source"] == "template"


@pytest.mark.parametrize("empty", ["", "   "])
def test_an_empty_llm_answer_falls_back(empty):
    def blank_chat(messages):
        return empty

    draft = prose.draft_summary(CARD, chat=blank_chat)
    assert draft["source"] == "template"
    assert draft["text"].strip()


def test_a_number_the_card_does_not_have_falls_back():
    def inventive_chat(messages):
        return "Marginaali on +9,99 dB, joten tapaus on kriittinen."

    draft = prose.draft_summary(CARD, chat=inventive_chat)
    assert draft["source"] == "template_guard"
    assert "+3,24" in draft["text"]


def test_a_clean_llm_answer_is_kept():
    def good_chat(messages):
        return "Tapaus 3074-103500417: PFD -184,78 dB(W/m²/Hz), marginaali +3,24 dB."

    draft = prose.draft_summary(CARD, chat=good_chat)
    assert draft["source"] == "llm"
    assert draft["text"].startswith("Tapaus 3074-103500417")


def test_a_configured_endpoint_is_called(monkeypatch):
    calls = []

    def fake_chat(messages):
        calls.append(messages)
        return "COMPASS-80E, marginaali +3,24 dB."

    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "granite")
    monkeypatch.setattr("app.llm.chat", fake_chat)
    draft = prose.draft_summary(CARD)
    assert draft["source"] == "llm"
    assert draft["model"] == "granite"
    assert len(calls) == 1
    assert "COMPASS-80E" in calls[0][0]["content"]

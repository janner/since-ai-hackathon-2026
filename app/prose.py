"""Prose for a card: the LLM drafts it, the guard checks it, the template is the floor.

The numbers always come from the card. If the LLM is missing, fails, or writes a number
that is not in the card, the deterministic template is used and the source is recorded.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from app import guard
from app.config import fmt_mhz, fmt_num

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
PROMPT = (
    "Write two plain sentences for a radio interference screening case. Use only the facts "
    "and numbers in this JSON. Do not invent numbers. Do not give a verdict.\n\n{card}"
)


def draft_letter(card: dict, chat: Callable | None = None) -> dict:
    return _draft(card, "correspondence_fi_en.md", chat)


def draft_summary(card: dict, chat: Callable | None = None) -> dict:
    return _draft(card, "case_fi.md", chat)


def _draft(card: dict, template_name: str, chat: Callable | None) -> dict:
    text = _ask(card, chat)
    if text is not None and not guard.check(text, card):
        return {"source": "llm", "text": text.strip()}
    source = "template" if text is None else "template_guard"
    return {"source": source, "text": template(card, template_name)}


def _ask(card: dict, chat: Callable | None) -> str | None:
    if chat is None:
        if not os.environ.get("LLM_BASE_URL"):
            return None  # no endpoint configured: the template is the product
        from app import llm

        chat = llm.chat
    try:
        text = chat([{"role": "user", "content": PROMPT.format(card=card)}])
        # A blank or whitespace answer is a failure, not prose: fall back to the template.
        return text if text and text.strip() else None
    except Exception:
        # An LLM that is down must not stop a run that is otherwise deterministic.
        return None


def template(card: dict, template_name: str = "case_fi.md") -> str:
    calc = card["calculation"]
    values = {
        "case_id": card["case_id"],
        "satellite": card["coverage"]["sat_name"] or "the notified satellite",
        "admin": card["parties"]["admin"],
        "beam": card["coverage"]["beam"],
        "band": (
            f"{fmt_mhz(card['band']['freq_min_mhz'])}-{fmt_mhz(card['band']['freq_max_mhz'])}"
        ),
        "station": card["victim"]["station"],
        "elevation": fmt_num(card["coverage"]["elevation_deg"]),
        "pfd": fmt_num(calc["pfd_dbw_m2_hz"]),
        "limit": fmt_num(calc["limit_dbw_m2_hz"]),
        "margin": f"{calc['margin_db']:+.2f}".replace(".", ","),
        "class": card["class"],
        "services": card["m4"]["services_in_finland"],
        "question": card["next_action"]["question"],
    }
    return (TEMPLATES / template_name).read_text(encoding="utf-8").format(**values)

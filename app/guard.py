"""Numeric guard: every number the prose claims must exist in the card.

The card is the source of truth; the LLM only writes sentences. A number that is not in
the card means the model invented it and the prose is replaced by the template.
"""

from __future__ import annotations

import json
import re

# A sign right after a digit is a range separator ("3 662-3 698"), not a minus.
_NUMBER_RE = re.compile(r"(?<!\d)[-−+]?\d+(?:[.,]\d+)?")
# A Finnish "3 662" is one number; join digits that are only separated by a space.
_SPACE_IN_NUMBER_RE = re.compile(r"(?<=\d)[\s\u00a0](?=\d)")


def scan(text: str) -> list[tuple[str, float]]:
    """Normalised numbers of a text as (as written, value)."""
    plain = _SPACE_IN_NUMBER_RE.sub("", text)
    found = []
    for match in _NUMBER_RE.finditer(plain):
        raw = match.group(0)
        try:
            found.append((raw, float(raw.replace("−", "-").replace(",", "."))))
        except ValueError:
            continue
    return found


def check(text: str, card: dict, tol: float = 0.01) -> list[str]:
    """Numbers of `text` that do not occur in the card. Empty list = accepted.

    The sign counts: "-60,44 dB" against a card margin of +60,44 is a wrong claim.
    """
    known = {value for _, value in scan(json.dumps(card, ensure_ascii=False))}
    return [
        raw
        for raw, value in scan(text)
        if not any(abs(value - candidate) <= tol for candidate in known)
    ]

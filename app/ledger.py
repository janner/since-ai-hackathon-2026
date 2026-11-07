"""Append-only complaint ledger: one event per JSON line, the state folded from the events.

A *complaint* is a Traficom contact to another administration about a Kaista case (a letter or a
remark) and its lifecycle. A ledger file is only ever appended to: no code path here edits or
deletes a line (five-year audit). The state of a complaint is derived by folding its events in
order, never stored. Real runs write `ledger/complaints.jsonl`; the demo history writes
`ledger/complaints.synthetic.jsonl` with `synthetic: true` on every line, so a synthetic figure can
never be read as a real one.

Classification is a closed list (`EVENT_TYPES`/`ISSUE_TYPES`/`ACTIONS`/`OUTCOMES`); a free `note`
is allowed anywhere. `validate()` is what the API turns into a 422, so the statistics cannot be
filled from a free-text label.

Payload key mapping from the card (`app.cards.build_card`): `regulatory_stage.provision` ->
`regulatory_stage`, `audit.input_sha256` -> `source_sha256`, `audit.rules_version` -> `rules_version`,
`m4.services_in_finland` -> `m4_services`. The identifiers are copied, never referenced: a card from
an old run may not exist five years from now.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from statistics import median

REPO_ROOT = Path(__file__).resolve().parent.parent

EVENT_TYPES = ("opened", "letter_sent", "reply_received", "action_recorded", "closed", "reopened")
ISSUE_TYPES = (
    "pfd_exceedance",
    "near_limit",
    "band_without_satellite_allocation",
    "missing_data",
    "terrestrial_field_strength",
)
ACTIONS = ("comment_sent", "coordination_requested", "br_assistance_requested", "no_action_decided")
OUTCOMES = (
    "filing_modified",
    "filing_withdrawn",
    "coordination_agreement",
    "no_reply",
    "rejected_by_counterparty",
    "no_action_needed",
    "pending",
)
# A closed complaint cannot be closed as "pending"; that is what an open one looks like.
CLOSE_OUTCOMES = tuple(o for o in OUTCOMES if o != "pending")
# Which closed list a payload key must come from, when the event carries that key at all.
PAYLOAD_LISTS = {"issue_type": ISSUE_TYPES, "action": ACTIONS, "outcome": OUTCOMES}
# The card's class -> the complaint's issue_type; classes outside this map open no complaint.
CLASS_ISSUES = {
    "exceeds": "pfd_exceedance",
    "near": "near_limit",
    "not_space": "band_without_satellite_allocation",
}


def ledger_dir() -> Path:
    """KAISTA_LEDGER overrides the default `<repo>/ledger` (tests, a second register)."""
    return Path(os.environ.get("KAISTA_LEDGER", REPO_ROOT / "ledger"))


def events_path(synthetic: bool = False, directory: Path | None = None) -> Path:
    name = "complaints.synthetic.jsonl" if synthetic else "complaints.jsonl"
    return (directory or ledger_dir()) / name


def now() -> str:
    """The current instant with the machine's UTC offset (Europe/Helsinki on the demo host)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def event(
    complaint_id: str,
    type: str,
    at: str,
    actor: str,
    payload: dict | None = None,
    synthetic: bool = False,
) -> dict:
    """One ledger event with a deterministic event_id (same content -> same id)."""
    body = {
        "complaint_id": complaint_id,
        "at": at,
        "type": type,
        "actor": actor,
        "synthetic": bool(synthetic),
        "payload": dict(payload or {}),
    }
    validate(body)
    digest = hashlib.sha256(
        json.dumps(
            [complaint_id, type, at, actor, body["payload"]],
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()[:16]
    return {"event_id": digest, **body}


def validate(ev: dict) -> None:
    """Raise ValueError for anything the closed lists do not cover. The API maps it to 422."""
    where = f"{ev.get('complaint_id')}/{ev.get('type')}"
    if not ev.get("complaint_id"):
        raise ValueError("complaint_id is required")
    if ev.get("type") not in EVENT_TYPES:
        raise ValueError(f"{where}: unknown event type {ev.get('type')!r}")
    if not ev.get("at"):
        raise ValueError(f"{where}: at is required")
    if not isinstance(ev.get("payload") or {}, dict):
        raise ValueError(f"{where}: payload must be an object")
    payload = ev.get("payload") or {}
    for key, allowed in PAYLOAD_LISTS.items():
        value = payload.get(key)
        if value is not None and value not in allowed:
            raise ValueError(f"{where}: unknown {key} {value!r}; allowed: {', '.join(allowed)}")
    if ev["type"] == "opened" and payload.get("issue_type") not in ISSUE_TYPES:
        raise ValueError(f"{where}: opened needs a known issue_type")
    if ev["type"] == "action_recorded" and payload.get("action") not in ACTIONS:
        raise ValueError(f"{where}: action_recorded needs a known action")
    if ev["type"] == "closed" and payload.get("outcome") not in CLOSE_OUTCOMES:
        raise ValueError(f"{where}: closed needs a known outcome (not 'pending')")


def read(synthetic: bool = False, directory: Path | None = None) -> list[dict]:
    """Every event in one ledger file, in file order; a missing file is an empty ledger."""
    try:
        text = events_path(synthetic, directory).read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def load(synthetic: bool = True, directory: Path | None = None) -> list[dict]:
    """The real log, plus the synthetic demo history unless synthetic=False."""
    events = read(False, directory)
    if synthetic:
        events += read(True, directory)
    return events


def append(new: list[dict], synthetic: bool = False, directory: Path | None = None) -> list[dict]:
    """Append events. The file is opened in append mode only; nothing here rewrites a line."""
    for ev in new:
        validate(ev)
    path = events_path(synthetic, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for ev in new:
            handle.write(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n")
    return new


def write_all(events: list[dict], directory: Path | None = None) -> Path:
    """Write a whole ledger file at once. The seeder only: real events are appended, never rewritten."""
    for ev in events:
        validate(ev)
    path = events_path(synthetic=True, directory=directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(ev, ensure_ascii=False, sort_keys=True) + "\n" for ev in events),
        encoding="utf-8",
    )
    return path


def days_between(start: str, end: str) -> int:
    return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days


def complaints(events: list[dict]) -> list[dict]:
    """Fold the log into complaints, in first-appearance order.

    A complaint without its `opened` line is not a complaint and is dropped (the API cannot create
    one that way, so this only guards a hand-edited file).
    """
    grouped: dict[str, list[dict]] = {}
    for ev in events:
        grouped.setdefault(ev["complaint_id"], []).append(ev)

    out = []
    for complaint_id, group in grouped.items():
        group = sorted(group, key=lambda e: e["at"])
        opened = next((e for e in group if e["type"] == "opened"), None)
        if opened is None:
            continue
        letters = [e for e in group if e["type"] == "letter_sent"]
        closed_at, outcome = None, "pending"
        status = "open"
        for ev in group:
            if ev["type"] == "closed":
                status, closed_at = "closed", ev["at"]
                outcome = ev["payload"]["outcome"]
            elif ev["type"] == "reopened":
                status, closed_at = "open", None
        reply = next((e for e in group if e["type"] == "reply_received"), None)
        start = letters[0]["at"] if letters else opened["at"]
        end = (reply or {}).get("at") or closed_at
        payload = opened["payload"]
        recorded = {e["payload"]["action"] for e in group if e["type"] == "action_recorded"}
        out.append(
            {
                "complaint_id": complaint_id,
                "synthetic": bool(opened.get("synthetic")),
                "at": opened["at"],
                "status": status,
                "outcome": outcome,
                "days_to_reply": days_between(start, end) if end else None,
                "ific": payload.get("ific"),
                "case_id": payload.get("case_id"),
                "ntc_id": payload.get("ntc_id"),
                "adm": payload.get("adm"),
                "network_org": payload.get("network_org"),
                "sat_name": payload.get("sat_name"),
                "band": payload.get("band"),
                "m4_services": payload.get("m4_services"),
                "class": payload.get("class"),
                "issue_type": payload.get("issue_type"),
                "same_network": list(payload.get("same_network") or ()),
                # A letter is a comment sent; the rest are the recorded decisions.
                "actions": sorted(recorded | ({"comment_sent"} if letters else set())),
                "letters": [e["payload"].get("letter") for e in letters],
                "events": group,
            }
        )
    return out


def open_complaint(events: list[dict], case_id: str, same_network: tuple = ()) -> str | None:
    """The complaint still open for this case, or None. A re-run of the same case opens nothing.

    `same_network` is the card's own chain (other notices of the same network), so a second notice
    of a network already under an open complaint does not open a second one.
    """
    keys = {case_id, *same_network}
    for complaint in complaints(events):
        if complaint["status"] != "open":
            continue
        if complaint["case_id"] in keys or keys & set(complaint["same_network"]):
            return complaint["complaint_id"]
    return None


def median_days(items: list[dict]) -> float | None:
    """The median days from letter to reply over the complaints that have one."""
    values = [i["days_to_reply"] for i in items if i["days_to_reply"] is not None]
    return round(median(values), 1) if values else None

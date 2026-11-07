"""Read-only API and one page over what the pipeline wrote.

The UI never computes: every number on the page comes from the files
app.pipeline wrote into out/. No LLM call, no network, no new calculation.
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from app import ledger, stats
from app.gates import CLASS_ORDER

app = FastAPI(title="Kaista")
STATIC = Path(__file__).parent / "static"
REPO_ROOT = Path(__file__).resolve().parent.parent

NEED_PIPELINE = "run `python -m app.pipeline` first"
NEED_MONITOR = "run `python scripts/monitor.py --check` first"


def status_dir() -> Path:
    """Where the monitor keeps fetch_status.json: KAISTA_OUT, else out/."""
    return Path(os.environ.get("KAISTA_OUT", REPO_ROOT / "out"))


def out_dir() -> Path:
    """The run the page shows: KAISTA_OUT, else the monitor's runs/latest, else out/."""
    pinned = os.environ.get("KAISTA_OUT")
    if pinned:
        return Path(pinned)
    latest = REPO_ROOT / "runs" / "latest"
    return latest if latest.is_dir() else REPO_ROOT / "out"


def load(name: str) -> Any:
    path = out_dir() / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # 503, not 500: a missing or half-written run is an expected state, not a bug here.
        raise HTTPException(503, f"{path}: {exc}. {NEED_PIPELINE}") from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/funnel")
def funnel() -> Any:
    return load("funnel.json")


@app.get("/api/cases")
def cases() -> Any:
    return load("cases.json")


@app.get("/api/cases/{case_id}")
def case(case_id: str) -> Any:
    for item in load("cases.json"):
        if item.get("case_id") == case_id:
            return item
    raise HTTPException(404, f"tuntematon case_id: {case_id}")


@app.get("/api/queue")
def queue() -> Any:
    """cases.json in queue order: regulatory stage, then class, then the deadline.

    shortcut: cannot_decide notices have no card in cases.json, so they are absent
    from this list; the funnel endpoint carries their count. Upgrade if the UI must
    show them as queue rows (then read out/queue.md instead).
    """
    order = {klass: i for i, klass in enumerate(CLASS_ORDER)}

    def key(case: dict) -> tuple:
        stage_info = case.get("regulatory_stage")
        stage = 9
        if isinstance(stage_info, dict) and isinstance(stage_info.get("rank"), int):
            stage = stage_info["rank"]
        klass = order.get(case.get("class"), len(order))
        deadline = case.get("deadline")
        if not deadline:
            deadline_rank, ordinal = 2, 0
        else:
            day, month, year = (int(part) for part in deadline.split("."))
            stamp = date(year, month, day).toordinal()
            deadline_rank, ordinal = (1, -stamp) if case.get("deadline_passed") else (0, stamp)
        return (stage, klass, deadline_rank, ordinal, case["case_id"])

    return sorted(load("cases.json"), key=key)


def run_monitor() -> None:
    """Ask ITU now, synchronously; the UI button waits for the answer.

    A timeout is a 504 so the UI shows a failed check instead of the last good status.
    """
    try:
        subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "monitor.py"), "--check"],
            cwd=REPO_ROOT,
            check=False,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(504, "tarkistus aikakatkaistiin (180 s)") from exc


@app.get("/api/fetch-status")
def fetch_status() -> Any:
    """The last monitor check: status no_new | new | error (see scripts/monitor.py)."""
    path = status_dir() / "fetch_status.json"
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(503, f"{path}: {exc}. {NEED_MONITOR}") from exc
    if check_locked():
        status["check_locked"] = True
    return status


def check_locked() -> bool:
    """KAISTA_CHECK_LOCKED=1 freezes the shown run (user tests, recorded demos)."""
    return os.environ.get("KAISTA_CHECK_LOCKED") == "1"


@app.post("/api/fetch-check")
def fetch_check() -> Any:
    """Check ITU for a new IFIC and return the fresh status. Errors travel in the file."""
    if check_locked():
        raise HTTPException(403, "Check now is switched off on this demo.")
    run_monitor()
    return fetch_status()


class ComplaintEvent(BaseModel):
    """One human decision on a complaint. Closed lists only; `note` is free text."""

    type: str
    actor: str = "spec-01"  # a pseudonym, never a real name
    at: str | None = None
    payload: dict[str, Any] = {}


def ledger_complaints(synthetic: bool = True) -> list[dict]:
    return ledger.complaints(ledger.load(synthetic=synthetic))


@app.get("/api/complaints")
def complaints(
    adm: str | None = None,
    sat_name: str | None = None,
    band: str | None = None,
    issue_type: str | None = None,
    status: str | None = None,
    year: int | None = None,
    synthetic: bool = True,
) -> Any:
    """The complaint register, newest filters first. `synthetic=false` hides the demo history."""
    return stats.matching(
        ledger_complaints(synthetic),
        year=year,
        adm=adm,
        sat_name=sat_name,
        band=band,
        issue_type=issue_type,
        status=status,
    )


@app.get("/api/complaints/{complaint_id}")
def complaint(complaint_id: str) -> Any:
    """One complaint with its whole event history, in order."""
    for item in ledger_complaints():
        if item["complaint_id"] == complaint_id:
            return item
    raise HTTPException(404, f"tuntematon complaint_id: {complaint_id}")


@app.post("/api/complaints/{complaint_id}/events", status_code=201)
def record_event(complaint_id: str, body: ComplaintEvent) -> Any:
    """Record a human decision. An unknown type or list value is a 422, and an event without its
    complaint is a 404: the log stays a log of complaints, not of loose events."""
    known = any(item["complaint_id"] == complaint_id for item in ledger_complaints())
    if body.type != "opened" and not known:
        raise HTTPException(404, f"tuntematon complaint_id: {complaint_id}")
    try:
        event = ledger.event(
            complaint_id, body.type, body.at or ledger.now(), body.actor, body.payload
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    ledger.append([event])
    return event


def stats_report(
    from_: str | None,
    to: str | None,
    adm: str | None,
    sat_name: str | None,
    band: str | None,
    issue_type: str | None,
    year: int | None,
    synthetic: bool,
) -> dict:
    summary, _ = stats.report(
        synthetic=synthetic,
        year=year,
        adm=adm,
        sat_name=sat_name,
        band=band,
        issue_type=issue_type,
        start=from_,
        end=to,
    )
    return summary


@app.get("/api/stats")
def stats_view(
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
    adm: str | None = None,
    sat_name: str | None = None,
    band: str | None = None,
    issue_type: str | None = None,
    year: int | None = None,
    synthetic: bool = True,
) -> Any:
    """What was complained about, who it was about, and what was done. All of it from the events."""
    return stats_report(from_, to, adm, sat_name, band, issue_type, year, synthetic)


@app.get("/api/stats.csv")
def stats_export(
    from_: str | None = Query(None, alias="from"),
    to: str | None = None,
    adm: str | None = None,
    sat_name: str | None = None,
    band: str | None = None,
    issue_type: str | None = None,
    year: int | None = None,
    synthetic: bool = True,
) -> Any:
    """The same rows as the statistics view, flattened for a spreadsheet."""
    summary = stats_report(from_, to, adm, sat_name, band, issue_type, year, synthetic)
    buffer = io.StringIO()
    fields = ("section", "key", "count", "open", "repeat", "median_days", "outcomes", "network_org")
    writer = csv.DictWriter(buffer, fieldnames=fields)
    writer.writeheader()
    writer.writerows(stats.csv_rows(summary))
    return PlainTextResponse(buffer.getvalue(), media_type="text/csv; charset=utf-8")

"""Read-only API and one page over what the pipeline wrote.

The UI never computes: every number on the page comes from the files
app.pipeline wrote into out/. No LLM call, no network, no new calculation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

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


def margin_db(case: dict) -> float:
    value = case.get("calculation", {}).get("margin_db")
    return float(value) if isinstance(value, int | float) else 0.0


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
    """cases.json in queue order: class order, biggest margin first.

    shortcut: cannot_decide notices have no card in cases.json, so they are absent
    from this list; the funnel endpoint carries their count. Upgrade if the UI must
    show them as queue rows (then read out/queue.md instead).
    """
    order = {klass: i for i, klass in enumerate(CLASS_ORDER)}
    return sorted(
        load("cases.json"),
        key=lambda case: (
            order.get(case.get("class"), len(order)),
            -margin_db(case),
            case["case_id"],
        ),
    )


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

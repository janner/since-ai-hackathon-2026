"""Read-only API and one page over what the pipeline wrote.

The UI never computes: every number on the page comes from the files
app.pipeline wrote into out/. No LLM call, no network, no new calculation.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.config import QUEUE_CAP
from app.gates import CLASS_ORDER

app = FastAPI(title="Kaista")
STATIC = Path(__file__).parent / "static"

NEED_PIPELINE = "run `python -m app.pipeline` first"


def out_dir() -> Path:
    """KAISTA_OUT points the API at another output directory (tests use a tmp dir)."""
    return Path(os.environ.get("KAISTA_OUT", "out"))


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
    """cases.json in queue order: class order, biggest margin first, cap 20.

    shortcut: cannot_decide notices have no card in cases.json, so they are absent
    from this list; the funnel endpoint carries their count. Upgrade if the UI must
    show them as queue rows (then read out/queue.md instead).
    """
    order = {klass: i for i, klass in enumerate(CLASS_ORDER)}
    items = sorted(
        load("cases.json"),
        key=lambda case: (
            order.get(case.get("class"), len(order)),
            -margin_db(case),
            case["case_id"],
        ),
    )
    return items[:QUEUE_CAP]

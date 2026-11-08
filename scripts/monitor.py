"""Monitor ITU BR IFIC for the next space IFIC and ingest it when it appears.

    uv run python scripts/monitor.py --check     # ask ITU now, ingest a new package
    uv run python scripts/monitor.py             # print the last known status
    uv run python scripts/monitor.py --json      # print the status as JSON

The check reads the last ingested IFIC (runs/latest, then out/run.log, then
data/last_ific.txt), tries the next space BR IFIC at
https://www.itu.int/sns/ific10/ific<n>.zip and writes out/fetch_status.json.
No package yet (404, an HTML page instead of a zip, or a non-zip body) is
"no_new", exit 0. A network error is "error", exit 1.

A new package runs the funnel into runs/<ific>/ and only a clean run moves the
runs/latest pointer. out/ is never touched: it keeps the 3074 outputs the brief
asks for as separate files. A failed run never moves runs/latest and leaves out/
untouched; a half-written runs/<ific>/ is wiped by the next attempt.

Nothing is installed: the cadence is one line in whatever scheduler already exists, e.g.
    */30 * * * * cd /repo && uv run python scripts/monitor.py --check >> out/monitor.log 2>&1
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
IFIC_URL = "https://www.itu.int/sns/ific10/ific{}.zip"
UA = {"User-Agent": "Mozilla/5.0 (since-ai-2026 monitor)"}
CADENCE = timedelta(days=14)  # ITU publishes the space BR IFIC every two weeks
DOCUMENT = "space"  # the feed is sns/ific10, the space BR IFIC series


def control_dir() -> Path:
    """Where the monitor keeps fetch_status.json: KAISTA_OUT, else out/."""
    return Path(os.environ.get("KAISTA_OUT", REPO_ROOT / "out"))


def runs_dir() -> Path:
    """Per-package runs live next to the control dir, under runs/."""
    return control_dir().parent / "runs"


def current_dir() -> Path:
    """The run in use: runs/latest when it exists, else the control dir."""
    latest = runs_dir() / "latest"
    return latest if latest.is_dir() else control_dir()


def now() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def last_ific() -> int | None:
    """The IFIC ingested last: runs/latest, out/run.log's `ific=` line, or data/last_ific.txt."""
    latest = runs_dir() / "latest"
    if latest.is_dir():
        digits = "".join(c for c in latest.resolve().name if c.isdigit())
        if digits:
            return int(digits)
    log = current_dir() / "run.log"
    if log.is_file():
        for line in log.read_text(encoding="utf-8").splitlines():
            if line.startswith("ific="):
                digits = "".join(c for c in line.split("=", 1)[1] if c.isdigit())
                if digits:
                    return int(digits)
    fallback = REPO_ROOT / "data" / "last_ific.txt"
    if fallback.is_file():
        digits = "".join(c for c in fallback.read_text(encoding="utf-8") if c.isdigit())
        if digits:
            return int(digits)
    return None


def download(url: str) -> bytes | None:
    """The next space IFIC zip, or None when ITU has no such package yet.

    ITU answers an unpublished number with 404, or with a small HTML page and status 200
    when the request carries no browser User-Agent. Only bytes that start with `PK` are a
    package; anything else counts as "not published".
    """
    try:
        with urlopen(Request(url, headers=UA), timeout=60) as response:
            body = response.read()
    except HTTPError as error:
        if error.code == 404:
            return None
        raise
    return body if body.startswith(b"PK") else None


def extract_mdb(body: bytes, ific: int, work: Path) -> Path:
    """Write the zip and pull the single .mdb out of it (same shape as fetch_data.py)."""
    zip_path = work / f"ific{ific}.zip"
    zip_path.write_bytes(body)
    with zipfile.ZipFile(zip_path) as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith(".mdb"))
        archive.extract(name, work)
        mdb = work / Path(name).name
        if work / name != mdb:
            (work / name).replace(mdb)
    return mdb


def run_pipeline(ific_mdb: Path, out: Path) -> int:
    """Run the funnel on the freshly extracted MDB. Returns the process exit code.

    The space run only; the terrestrial side feature stays a separate concern.
    """
    command = [
        sys.executable,
        "-m",
        "app.pipeline",
        "--ific",
        str(ific_mdb),
        "--register",
        str(REPO_ROOT / "data" / "frequencies_of_interest.csv"),
        "--m4",
        str(REPO_ROOT / "data" / "taajuusjakotaulukko.json"),
        "--out",
        str(out),
    ]
    return subprocess.run(command, cwd=REPO_ROOT).returncode


def write_status(directory: Path, status: dict) -> None:
    """Write directory/fetch_status.json atomically so a reader never sees half a file."""
    directory.mkdir(parents=True, exist_ok=True)
    tmp = directory / "fetch_status.json.tmp"
    tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(directory / "fetch_status.json")


def read_status(directory: Path) -> dict | None:
    try:
        return json.loads((directory / "fetch_status.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def point_latest(runs: Path, ific: int) -> None:
    """Point runs/latest at the fresh run; the API and the UI follow this symlink."""
    tmp = runs / "latest.new"
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    tmp.symlink_to(str(ific))
    tmp.replace(runs / "latest")


def ingest(ific: int, body: bytes) -> dict:
    runs = runs_dir()
    target = runs / str(ific)
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    work = Path(tempfile.mkdtemp(prefix=f"ific{ific}-"))
    try:
        mdb = extract_mdb(body, ific, work)
        code = run_pipeline(mdb, target)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if code != 0 or not (target / "funnel.json").is_file():
        status = {
            "status": "error",
            "document": DOCUMENT,
            "last_ific": ific - 1,
            "checked_at": now(),
            "message": f"new package ific{ific} was fetched but the pipeline failed "
            f"(exit {code}); out/ was left unchanged",
        }
        write_status(control_dir(), status)
        return status
    point_latest(runs, ific)
    counts = json.loads((target / "funnel.json").read_text(encoding="utf-8")).get("counts", {})
    status = {
        "status": "new",
        "document": DOCUMENT,
        "ific": ific,
        "counts": counts,
        "run_at": now(),
        "message": f"uusi paketti ific{ific} haettu ja ajettu (runs/{ific})",
    }
    write_status(control_dir(), status)
    return status


def check() -> dict:
    last = last_ific()
    checked_at = now()
    if last is None:
        status = {
            "status": "error",
            "document": DOCUMENT,
            "checked_at": checked_at,
            "message": "the latest IFIC identifier was not found "
            "(runs/latest, out/run.log or data/last_ific.txt)",
        }
        write_status(control_dir(), status)
        return status
    try:
        body = download(IFIC_URL.format(last + 1))
    except (URLError, OSError, TimeoutError, HTTPException) as error:
        status = {
            "status": "error",
            "document": DOCUMENT,
            "last_ific": last,
            "checked_at": checked_at,
            "message": f"ITU did not answer: {error}",
        }
        write_status(control_dir(), status)
        return status
    if body is None:
        status = {
            "status": "no_new",
            "document": DOCUMENT,
            "last_ific": last,
            "checked_at": checked_at,
            "next_check": (datetime.now(UTC).astimezone() + CADENCE).isoformat(timespec="seconds"),
            "message": f"a new IFIC package has not been published yet (latest {last})",
        }
        write_status(control_dir(), status)
        return status
    try:
        return ingest(last + 1, body)
    except (HTTPException, OSError, TimeoutError, zipfile.BadZipFile, StopIteration) as error:
        # A truncated body, a corrupt zip or a zip without .mdb must not crash the check;
        # write the error the way a network failure does, so the UI never shows a stale success.
        status = {
            "status": "error",
            "document": DOCUMENT,
            "last_ific": last,
            "checked_at": checked_at,
            "message": f"new package ific{last + 1} was broken or the pipeline crashed: {error}",
        }
        write_status(control_dir(), status)
        return status


def render(status: dict) -> str:
    kind = status.get("status")
    when = status.get("run_at") or status.get("checked_at") or ""
    if kind == "new":
        return f"new IFIC {status.get('ific')} fetched and run {when}"
    if kind == "error":
        return f"check failed {when}: {status.get('message', '')}"
    if kind == "no_new":
        return f"no new IFIC package (latest {status.get('last_ific')}), checked {when}"
    return status.get("message", "the check has not run yet")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/monitor.py",
        description="Monitor ITU BR IFIC and ingest a new space package.",
    )
    parser.add_argument("--check", action="store_true", help="ask ITU now and ingest a new package")
    parser.add_argument("--json", action="store_true", help="print the status as JSON")
    args = parser.parse_args(argv)
    if args.check:
        status = check()
    else:
        status = read_status(control_dir()) or {
            "status": "unknown",
            "message": "the check has not run yet",
        }
    print(json.dumps(status, ensure_ascii=False, indent=2) if args.json else render(status))
    return 1 if args.check and status["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())

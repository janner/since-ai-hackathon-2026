"""Monitor tests: the network and the pipeline are stubbed, out/ is a tmp directory."""

import io
import json
import zipfile
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from scripts import monitor


@pytest.fixture
def out(tmp_path, monkeypatch) -> Path:
    """A fake out/ with the last run at IFIC 3074, pointed at by KAISTA_OUT."""
    directory = tmp_path / "out"
    directory.mkdir()
    (directory / "run.log").write_text("ific=3074\nnotices=196\n", encoding="utf-8")
    (directory / "funnel.json").write_text(
        json.dumps({"counts": {"notices": 196}}), encoding="utf-8"
    )
    monkeypatch.setenv("KAISTA_OUT", str(directory))
    return directory


def responds(body: bytes):
    class Response:
        def read(self) -> bytes:
            return body

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    return lambda request, timeout=None: Response()


def raises(error: Exception):
    def call(request, timeout=None):
        raise error

    return call


def zip_with_mdb(name: str = "ific3075.mdb") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, b"Standard Jet DB fake")
    return buffer.getvalue()


def fake_pipeline(counts: dict, code: int = 0):
    def run(ific_mdb: Path, out: Path) -> int:
        if code == 0:
            (out / "funnel.json").write_text(json.dumps({"counts": counts}), encoding="utf-8")
            (out / "run.log").write_text("ific=3075\n", encoding="utf-8")
        return code

    return run


def untouched(out: Path) -> bool:
    return (out / "run.log").read_text(encoding="utf-8") == "ific=3074\nnotices=196\n"


def test_no_new_on_404(out, monkeypatch):
    monkeypatch.setattr(monitor, "urlopen", raises(HTTPError("u", 404, "Not Found", {}, None)))
    status = monitor.check()
    assert status["status"] == "no_new"
    assert status["last_ific"] == 3074
    assert status["next_check"] and status["checked_at"]
    assert monitor.main(["--check"]) == 0
    assert untouched(out)


def test_no_new_on_html_instead_of_zip(out, monkeypatch):
    monkeypatch.setattr(monitor, "urlopen", responds(b"<!DOCTYPE html><html>nope"))
    assert monitor.check()["status"] == "no_new"
    assert untouched(out)


def test_network_error_is_error_and_exit_1(out, monkeypatch):
    monkeypatch.setattr(monitor, "urlopen", raises(URLError("name resolution")))
    status = monitor.check()
    assert status["status"] == "error"
    assert "ITU" in status["message"]
    assert monitor.main(["--check"]) == 1
    assert untouched(out)  # an error never touches the run files
    assert not (out.parent / "runs" / "latest").exists()


def test_new_package_runs_the_pipeline_and_points_latest(out, monkeypatch):
    monkeypatch.setattr(monitor, "urlopen", responds(zip_with_mdb()))
    monkeypatch.setattr(monitor, "run_pipeline", fake_pipeline({"notices": 42, "exceeds": 7}))
    status = monitor.check()
    assert status["status"] == "new"
    assert status["ific"] == 3075
    assert status["counts"] == {"notices": 42, "exceeds": 7}
    assert status["run_at"]
    # the fresh run lives in runs/3075, runs/latest points at it, out/ is untouched
    runs = out.parent / "runs"
    assert json.loads((runs / "3075" / "funnel.json").read_text(encoding="utf-8"))["counts"]
    assert (runs / "latest").resolve() == runs / "3075"
    assert untouched(out)
    assert json.loads((out / "fetch_status.json").read_text(encoding="utf-8"))["ific"] == 3075
    assert monitor.last_ific() == 3075


def test_failed_run_keeps_out_and_runs_untouched(out, monkeypatch):
    monkeypatch.setattr(monitor, "urlopen", responds(zip_with_mdb()))
    monkeypatch.setattr(monitor, "run_pipeline", fake_pipeline({"notices": 42}, code=2))
    status = monitor.check()
    assert status["status"] == "error"
    assert "putki" in status["message"]
    assert monitor.main(["--check"]) == 1
    assert untouched(out)
    assert not (out.parent / "runs" / "latest").exists()


def test_truncated_download_is_error_and_exit_1(out, monkeypatch):
    # ITU closing the connection mid-body: http.client.IncompleteRead is an HTTPException,
    # not an OSError, so it must still be caught and turned into an error status.
    monkeypatch.setattr(monitor, "urlopen", raises(IncompleteRead(b"PK\x03\x04", 999)))
    status = monitor.check()
    assert status["status"] == "error"
    assert status["last_ific"] == 3074
    assert status["message"]
    assert monitor.main(["--check"]) == 1
    assert untouched(out)
    assert not (out.parent / "runs" / "latest").exists()


def test_broken_zip_is_error_and_exit_1(out, monkeypatch):
    # PK-magic but corrupt: zipfile.BadZipFile must not escape check().
    monkeypatch.setattr(monitor, "urlopen", responds(b"PK\x03\x04 not a real zip"))
    status = monitor.check()
    assert status["status"] == "error"
    assert monitor.main(["--check"]) == 1
    assert untouched(out)
    assert not (out.parent / "runs" / "latest").exists()


def test_zip_without_mdb_is_error_and_exit_1(out, monkeypatch):
    monkeypatch.setattr(monitor, "urlopen", responds(zip_with_mdb("readme.txt")))
    status = monitor.check()
    assert status["status"] == "error"
    assert monitor.main(["--check"]) == 1
    assert untouched(out)
    assert not (out.parent / "runs" / "latest").exists()


def test_status_file_is_valid_json_with_the_last_answer(out, monkeypatch):
    monkeypatch.setattr(monitor, "urlopen", raises(HTTPError("u", 404, "Not Found", {}, None)))
    monitor.check()
    saved = json.loads((out / "fetch_status.json").read_text(encoding="utf-8"))
    assert saved["status"] == "no_new"
    assert monitor.read_status(out) == saved


def test_missing_run_log_and_fallback_is_error(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor, "REPO_ROOT", tmp_path)  # no data/last_ific.txt either
    monkeypatch.setenv("KAISTA_OUT", str(tmp_path / "empty"))
    status = monitor.check()
    assert status["status"] == "error"
    assert "IFIC-tunnistetta" in status["message"]

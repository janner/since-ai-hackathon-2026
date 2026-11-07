"""API tests. Content comes from a real pipeline run; the error paths need no data."""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main, pipeline

ROOT = Path(__file__).resolve().parent.parent
SPACE_MDB = ROOT / "data" / "itu-ific-3074" / "ific3074.mdb"
REGISTER = ROOT / "data" / "frequencies_of_interest.csv"
M4 = ROOT / "data" / "taajuusjakotaulukko.json"
CLASSES = ("exceeds", "near", "cannot_decide", "clear")
needs_data = pytest.mark.skipif(
    not (SPACE_MDB.is_file() and REGISTER.is_file() and M4.is_file()),
    reason="challenge data missing: run scripts/fetch_data.py",
)


@pytest.fixture(scope="session")
def real_run(tmp_path_factory) -> Path:
    """One demo-slice run of the real MDB that the content tests read back."""
    out = tmp_path_factory.mktemp("api-run")
    assert pipeline.run(SPACE_MDB, REGISTER, M4, out) == 0
    return out


@pytest.fixture
def out_dir(tmp_path, monkeypatch, real_run) -> Path:
    """A private copy of the real run: a test may corrupt its own files."""
    directory = tmp_path / "out"
    shutil.copytree(real_run, directory)
    monkeypatch.setenv("KAISTA_OUT", str(directory))
    return directory


@pytest.fixture
def client(out_dir) -> TestClient:
    return TestClient(main.app)


@pytest.fixture
def bare_client(tmp_path, monkeypatch) -> TestClient:
    """No output directory at all: the page still loads, the API answers 503."""
    monkeypatch.setenv("KAISTA_OUT", str(tmp_path / "nope"))
    return TestClient(main.app)


def test_index_serves_the_finnish_page(bare_client):
    response = bare_client.get("/")
    assert response.status_code == 200
    for word in ("Kaista", "Suppilo", "Jono", "Kortti"):
        assert word in response.text


def test_health(bare_client):
    assert bare_client.get("/health").json() == {"ok": True}


def test_missing_out_is_503_and_the_page_still_loads(bare_client):
    response = bare_client.get("/api/cases")
    assert response.status_code == 503
    assert "app.pipeline" in response.json()["detail"]
    assert bare_client.get("/").status_code == 200


def test_broken_json_is_503_not_500(tmp_path, monkeypatch):
    directory = tmp_path / "out"
    directory.mkdir()
    (directory / "cases.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("KAISTA_OUT", str(directory))
    response = TestClient(main.app).get("/api/cases")
    assert response.status_code == 503
    assert "app.pipeline" in response.json()["detail"]


@pytest.mark.data
@needs_data
def test_funnel_numbers(client):
    body = client.get("/api/funnel").json()
    assert body["counts"] == {
        "notices": 196,
        "g1": 41,
        "g2": 19,
        "g3": 18,
        "cannot_decide": 1,
        "exceeds": 9,
        "near": 5,
        "clear": 4,
    }
    assert body["queue"] == {"shown": 15}


@pytest.mark.data
@needs_data
def test_cases_returns_every_card(client):
    body = client.get("/api/cases").json()
    assert isinstance(body, list) and len(body) == 18


@pytest.mark.data
@needs_data
def test_case_by_id(client):
    response = client.get("/api/cases/3074-103500417")
    assert response.status_code == 200
    assert response.json()["case_id"] == "3074-103500417"


@pytest.mark.data
@needs_data
def test_unknown_case_id_is_404(client):
    response = client.get("/api/cases/3074-999999")
    assert response.status_code == 404
    assert "3074-999999" in response.json()["detail"]


@pytest.mark.data
@needs_data
def test_queue_is_ordered_by_class(client):
    body = client.get("/api/queue").json()
    assert len(body) == 18  # no cap: every card is queued
    ranks = [CLASSES.index(item["class"]) for item in body]
    assert ranks == sorted(ranks)
    exceeds = [item["calculation"]["margin_db"] for item in body if item["class"] == "exceeds"]
    assert exceeds == sorted(exceeds, reverse=True)

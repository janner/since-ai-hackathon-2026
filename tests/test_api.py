"""API tests. Data-free: the fixtures write a synthetic out/ into tmp_path."""

import json

import pytest
from fastapi.testclient import TestClient

from app import main

CLASSES = ("exceeds", "near", "cannot_decide", "clear")

FUNNEL = {
    "input_sha256": "0" * 64,
    "rules_version": "1.1.0",
    "run_at": "2026-11-06T22:49:43+02:00",
    "mode": "slice",
    "counts": {
        "notices": 196,
        "g1": 41,
        "g2": 19,
        "g3": 18,
        "cannot_decide": 1,
        "exceeds": 9,
        "near": 5,
        "clear": 4,
    },
    "drops": {"no_band_overlap": 155},
    "queue": {"shown": 15},
}


def card(index: int, klass: str) -> dict:
    """One card in the shape out/cases.json holds, trimmed to what the UI reads."""
    ntc_id = str(1_000_000 + index)
    return {
        "case_id": f"3074-{ntc_id}",
        "same_network": [],
        "source": {"file": "ific3074.mdb", "tables": ["notice"], "keys": {"ntc_id": ntc_id}},
        "parties": {"admin": "CHN", "network_org": "", "adm_ref_id": ""},
        "band": {"freq_min_mhz": 3400.0, "freq_max_mhz": 3700.0, "bandwidth_mhz": 300.0},
        "direction": "space-to-Earth",
        "coverage": {"orbit": "NGSO", "sat_name": "CSN-SSO", "elevation_deg": 5.0, "beam": "CD"},
        "victim": {"station": "989011", "class": "MVV", "rx_mhz": 3596.4},
        "calculation": {
            "method": "PFD_peak_upper_bound",
            "pfd_dbw_m2_hz": -137.56,
            "limit_dbw_m2_hz": -198.0,
            "margin_db": float(60 - index),
            "distance_km": 2310,
        },
        "m4": {"rows": [4051], "services_in_finland": "Amateur"},
        "class": klass,
        "missing": ["s_beam.bore_long"],
        "next_action": {"counterparty": "CHN", "question": "?"},
        "audit": {},
        "prose": {"source": "template", "text": "Seloste"},
    }


@pytest.fixture
def cases() -> list[dict]:
    return [card(i, CLASSES[i % len(CLASSES)]) for i in range(18)]


@pytest.fixture
def out_dir(tmp_path, monkeypatch, cases):
    directory = tmp_path / "out"
    directory.mkdir()
    (directory / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
    (directory / "funnel.json").write_text(json.dumps(FUNNEL), encoding="utf-8")
    monkeypatch.setenv("KAISTA_OUT", str(directory))
    return directory


@pytest.fixture
def client(out_dir):
    return TestClient(main.app)


def test_index_serves_the_finnish_page(client):
    response = client.get("/")
    assert response.status_code == 200
    for word in ("Kaista", "Suppilo", "Jono", "Kortti"):
        assert word in response.text


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_funnel_numbers(client):
    body = client.get("/api/funnel").json()
    assert body["counts"] == FUNNEL["counts"]
    assert body["queue"] == {"shown": 15}


def test_cases_returns_every_card(client):
    body = client.get("/api/cases").json()
    assert isinstance(body, list) and len(body) == 18


def test_case_by_id(client):
    response = client.get("/api/cases/3074-1000000")
    assert response.status_code == 200
    assert response.json()["case_id"] == "3074-1000000"


def test_unknown_case_id_is_404(client):
    response = client.get("/api/cases/3074-999999")
    assert response.status_code == 404
    assert "3074-999999" in response.json()["detail"]


def test_queue_is_ordered_by_class(client, cases):
    body = client.get("/api/queue").json()
    assert len(body) == len(cases)  # no cap: every card is queued
    ranks = [CLASSES.index(item["class"]) for item in body]
    assert ranks == sorted(ranks)
    exceeds = [item for item in body if item["class"] == "exceeds"]
    assert [item["calculation"]["margin_db"] for item in exceeds] == sorted(
        (item["calculation"]["margin_db"] for item in exceeds), reverse=True
    )
    assert {item["case_id"] for item in body} <= {item["case_id"] for item in cases}


def test_missing_out_is_503_and_the_page_still_loads(client, tmp_path, monkeypatch):
    monkeypatch.setenv("KAISTA_OUT", str(tmp_path / "nope"))
    response = client.get("/api/cases")
    assert response.status_code == 503
    assert "app.pipeline" in response.json()["detail"]
    assert client.get("/").status_code == 200


def test_broken_json_is_503_not_500(client, out_dir):
    (out_dir / "cases.json").write_text("{not json", encoding="utf-8")
    response = client.get("/api/cases")
    assert response.status_code == 503
    assert "app.pipeline" in response.json()["detail"]

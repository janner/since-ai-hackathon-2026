from fastapi.testclient import TestClient

from app import llm, main

client = TestClient(main.app)


def test_health():
    assert client.get("/health").json() == {"ok": True}


def test_ask_uses_llm(monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda msgs, **kw: "echo:" + msgs[0]["content"])
    r = client.post("/api/ask", json={"question": "hi"})
    assert r.status_code == 200 and r.json() == {"answer": "echo:hi"}


def test_ask_llm_down_is_502(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("down")

    monkeypatch.setattr(llm, "chat", boom)
    assert client.post("/api/ask", json={"question": "hi"}).status_code == 502


def test_ask_rejects_empty():
    assert client.post("/api/ask", json={"question": ""}).status_code == 422

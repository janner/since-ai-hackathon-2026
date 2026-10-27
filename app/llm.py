"""Yksi OpenAI-yhteensopiva chat-kutsu. Palvelu vaihdetaan .env:llä, ei koodilla."""
import json
import os
import urllib.request


def chat(messages: list[dict], **params) -> str:
    base = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    body = {"model": os.environ.get("LLM_MODEL", ""), "messages": messages, **params}
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('LLM_API_KEY', '')}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["choices"][0]["message"]["content"]

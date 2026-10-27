from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app import llm

app = FastAPI(title="Since AI 2026")
STATIC = Path(__file__).parent / "static"


class Ask(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/ask")
def ask(body: Ask):
    try:
        answer = llm.chat([{"role": "user", "content": body.question}])
    except Exception as e:  # LLM-palvelu alhaalla -> selkeä virhe demossa, ei 500-pinoa
        raise HTTPException(502, f"LLM error: {e}") from e
    return {"answer": answer}

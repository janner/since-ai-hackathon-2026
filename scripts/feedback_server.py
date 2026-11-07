#!/usr/bin/env python3
"""Minimal feedback form server for the Kaista customer demo.

Binds 127.0.0.1 only; Tailscale Serve exposes it on the tailnet. Stores each
submission in ~/.hermes/hackathon-feedback/ and sends a best-effort Matrix note.
"""

from __future__ import annotations

import html
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parent.parent
FORM = ROOT / "feedback" / "index.html"
STORE = Path(os.environ.get("KAISTA_FEEDBACK_DIR", Path.home() / ".hermes" / "hackathon-feedback"))
TARGET = os.environ.get("KAISTA_FEEDBACK_TARGET", "matrix")
NOTIFY = os.environ.get("KAISTA_FEEDBACK_NOTIFY", "1") != "0"
MAX_BODY = 16 * 1024
FIELDS = ("name", "org", "useful", "understood", "missing", "feedback", "contact_ok", "contact")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clip(value: object, limit: int = 2000) -> str:
    return CONTROL.sub("", str(value or "")).strip()[:limit]


def entry_from(form: dict[str, list[str]]) -> tuple[dict | None, str | None]:
    data = {
        key: clip(
            (form.get(key) or [""])[0],
            500 if key in {"name", "org", "contact"} else 2000,
        )
        for key in FIELDS
    }
    if not data["feedback"] and not data["missing"]:
        return None, "Kirjoita palaute tai kerro, mitä jäit kaipaamaan."
    if data["useful"] and data["useful"] not in {"1", "2", "3", "4", "5"}:
        return None, "Valitse hyödyllisyys asteikolla 1–5."
    if data["understood"] and data["understood"] not in {"kylla", "osittain", "en"}:
        return None, "Valitse ymmärsitkö työkalun käytön."
    data["contact_ok"] = "yes" if data["contact_ok"] == "yes" else "no"
    data["id"] = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)
    data["received_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    return data, None


def markdown(entry: dict) -> str:
    understood = {"kylla": "Kyllä", "osittain": "Osittain", "en": "En"}.get(
        entry["understood"], entry["understood"]
    )
    lines = [f"## {entry['received_at']} · {entry['id']}", ""]
    pairs = [
        ("Nimi", entry["name"]),
        ("Organisaatio ja rooli", entry["org"]),
        ("Hyödyllisyys", entry["useful"] + "/5" if entry["useful"] else ""),
        ("Ymmärsikö", understood),
        ("Mitä jäi kaipaamaan", entry["missing"]),
        ("Vapaa palaute", entry["feedback"]),
    ]
    for label, value in pairs:
        if value:
            lines.append(f"- **{label}:** {value}")
    if entry["contact_ok"] == "yes":
        lines.append("- **Saa ottaa yhteyttä:** kyllä")
        if entry["contact"]:
            lines.append(f"- **Yhteystieto:** {entry['contact']}")
    return "\n".join(lines)


def store(entry: dict) -> None:
    STORE.mkdir(parents=True, exist_ok=True)
    with (STORE / "feedback.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    latest = json.dumps(entry, ensure_ascii=False, indent=2) + "\n"
    (STORE / "latest.json").write_text(latest, encoding="utf-8")
    text = markdown(entry)
    with (STORE / "feedback.md").open("a", encoding="utf-8") as fh:
        fh.write(text + "\n\n")
    (STORE / "latest.md").write_text(text + "\n", encoding="utf-8")


def notify(entry: dict) -> None:
    if not NOTIFY:
        return
    hermes = shutil.which("hermes")
    if not hermes:
        return
    text = "Uusi palaute Kaista-demosta\n\n" + markdown(entry)
    try:
        subprocess.run(
            [hermes, "send", "--to", TARGET, "--subject", "Uusi palaute: Kaista", text],
            timeout=15,
            capture_output=True,
            text=True,
        )
    except Exception:
        pass  # the file is the source of truth; a Matrix hiccup must not fail the form


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="fi">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  :root {{ --bg:#fff; --fg:#161616; --muted:#525252; --line:#e0e0e0; --accent:#0f62fe; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
          font:400 16px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,
               'DejaVu Sans',sans-serif; }}
  header {{ padding:16px 24px; border-bottom:1px solid var(--line); }}
  header h1 {{ margin:0; font-size:24px; font-weight:600; }}
  main {{ max-width:720px; margin:0 auto; padding:24px; }}
  h2 {{ margin:0 0 8px; font-size:20px; font-weight:600; }}
  p {{ margin:0 0 16px; }}
  .muted {{ color:var(--muted); font-size:14px; }}
  code {{ font:400 14px/1.5 'IBM Plex Mono',ui-monospace,monospace; }}
  a {{ color:var(--accent); }}
</style>
<header><h1>Kaista</h1><p class="muted">Palaute demosta</p></header>
<main>{body}</main>
</html>""".encode()


class Handler(BaseHTTPRequestHandler):
    server_version = "KaistaFeedback/1.0"

    def send_body(
        self,
        status: int,
        body: bytes,
        content_type: str = "text/html; charset=utf-8",
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self.send_body(200, FORM.read_bytes())
        elif self.path == "/health":
            self.send_body(200, b"ok", "text/plain; charset=utf-8")
        elif self.path == "/favicon.ico":
            self.send_body(204, b"")
        else:
            self.send_body(
                404,
                page(
                    "Ei löytynyt",
                    '<h2>Ei löytynyt</h2><p class="muted">Tätä sivua ei ole.</p>',
                ),
            )

    def do_POST(self) -> None:
        if self.path != "/api/feedback":
            self.send_body(404, b"not found", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self.send_body(
                413,
                page(
                    "Liian suuri",
                    '<h2>Liian suuri</h2><p class="muted">Palaute on liian pitkä.</p>',
                ),
            )
            return
        body = self.rfile.read(length).decode("utf-8", "replace")
        entry, error = entry_from(parse_qs(body, keep_blank_values=True))
        if error or entry is None:
            body = (
                "<h2>Tarkista palaute</h2>"
                f"<p>{html.escape(error or '')}</p>"
                '<p><a href="/">Takaisin lomakkeeseen</a></p>'
            )
            self.send_body(400, page("Tarkista palaute", body))
            return
        store(entry)
        threading.Thread(target=notify, args=(entry,), daemon=True).start()
        self.send_body(
            200,
            page(
                "Kiitos palautteesta",
                f"<h2>Kiitos palautteesta</h2><p>Palaute on tallennettu.</p>"
                '<p class="muted">Viite: <code>'
                f"{html.escape(entry['id'])}</code>. Voit sulkea tämän sivun.</p>",
            ),
        )


def main() -> None:
    port = int(os.environ.get("KAISTA_FEEDBACK_PORT", "8322"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"feedback server on 127.0.0.1:{port}; store={STORE}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

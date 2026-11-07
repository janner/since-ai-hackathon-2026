"""Deterministic Teams digest for one IFIC run: the numbers, the top three, one link.

Reads the files app/cards.py writes (out/funnel.json, out/cases.json) and builds one
incoming-webhook message per run. No bot, no Graph, no cron, no LLM: one message out.

    uv run python scripts/notify.py --dry-run            # print + write out/teams_message.*
    uv run python scripts/notify.py --dry-run --html     # ...plus a Teams-styled HTML preview
    TEAMS_WEBHOOK_URL=... uv run python scripts/notify.py --send

KAISTA_OUT points at another output directory; the default is the monitor's runs/latest,
or out/ when no run has been ingested. KAISTA_URL is the UI (default http://localhost:8000).
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Mirrors app/config.REGULATORY_STAGES so the digest reads only out/ and stays stdlib-only.
# Within a class a filing another administration can still influence (9.1/9.6) outranks one
# already recorded (11.2); that is why the top three is not a plain margin sort.
# shortcut: rank table copied from app/config.py, import it if the stage table starts growing.
CLASS_ORDER = ("exceeds", "near", "cannot_decide", "clear")
STAGE_RANK = {"No. 9.1": 0, "No. 9.6": 0, "No. 11.2": 1, "Resolution 49": 2}
UNKNOWN_RANK = 9
EMPTY_MESSAGE = "Käsitelty, ei uusia huomioitavia tapauksia."

# The HTML preview's CSS, kept as constants so the template lines stay readable.
_TEAMS_STYLE = (
    "margin:0;padding:24px;background:#f5f5f5;font:14px/1.5 'Segoe UI',sans-serif;color:#242424"
)
_CARD_STYLE = (
    "max-width:520px;background:#fff;border:1px solid #e1dfdd;border-radius:6px;padding:16px"
)


def fmt_num(value: float) -> str:
    """60.44 -> '60,44' (Finnish decimal comma)."""
    return f"{value:g}".replace(".", ",")


def load(out: Path) -> tuple[dict, list[dict]]:
    """The funnel counts and the case cards of this run."""
    counts = json.loads((out / "funnel.json").read_text(encoding="utf-8"))["counts"]
    cases = json.loads((out / "cases.json").read_text(encoding="utf-8"))
    return counts, cases


def ific_tag(cases: list[dict]) -> str:
    return cases[0]["source"]["ific"] if cases else "-"


def top_cases(cases: list[dict], limit: int = 3) -> list[dict]:
    """The first rows of the queue: class, then stage, then margin, then case id."""
    queue = [case for case in cases if case["class"] != "clear"]

    def key(case: dict) -> tuple:
        stage = case["regulatory_stage"]["provision"]
        return (
            CLASS_ORDER.index(case["class"]) if case["class"] in CLASS_ORDER else len(CLASS_ORDER),
            STAGE_RANK.get(stage, UNKNOWN_RANK),
            -(case["calculation"]["margin_db"] or 0.0),
            case["case_id"],
        )

    return sorted(queue, key=key)[:limit]


def queue_size(counts: dict) -> int:
    return sum(counts.get(klass, 0) for klass in ("exceeds", "near", "cannot_decide"))


def case_line(case: dict) -> str:
    margin = case["calculation"]["margin_db"]
    return (
        f"{case['source']['keys']['ntc_id']} — {case['class']}, "
        f"{case['regulatory_stage']['provision']}, {'-' if margin is None else fmt_num(margin)} dB"
    )


def build_message(counts: dict, top: list[dict], ific: str, url: str) -> str:
    """The markdown a human reads in the channel (and the file this demo hands over)."""
    total = queue_size(counts)
    if total == 0:
        return EMPTY_MESSAGE
    lines = [
        f"# BR IFIC {ific} — {total} huomioitavaa",
        "",
        f"Suppilo: {counts['notices']} → {counts['g1']} → {counts['g2']} → "
        f"{counts['g3']} + {counts['cannot_decide']}",
        f"Luokat: {counts['exceeds']} ylittää · {counts['near']} lähellä",
        "",
        "## Kiireellisimmät",
    ]
    lines += [f"{index}. {case_line(case)}" for index, case in enumerate(top, start=1)]
    lines += ["", f"Kaista: {url}"]
    return "\n".join(lines)


def build_card(counts: dict, top: list[dict], ific: str, url: str) -> dict:
    """The Adaptive Card envelope an incoming webhook accepts."""
    total = queue_size(counts)
    if total == 0:
        body = [{"type": "TextBlock", "wrap": True, "text": EMPTY_MESSAGE}]
    else:
        body = [
            {
                "type": "TextBlock",
                "size": "Medium",
                "weight": "Bolder",
                "text": f"BR IFIC {ific} — {total} huomioitavaa",
            },
            {
                "type": "TextBlock",
                "wrap": True,
                "text": f"Suppilo: {counts['notices']} → {counts['g1']} → {counts['g2']} → "
                f"{counts['g3']} + {counts['cannot_decide']}",
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Ylittää", "value": str(counts["exceeds"])},
                    {"title": "Lähellä", "value": str(counts["near"])},
                    {"title": "Ei ratkaistavissa", "value": str(counts["cannot_decide"])},
                ],
            },
            {"type": "TextBlock", "weight": "Bolder", "text": "Kiireellisimmät"},
            {
                "type": "TextBlock",
                "wrap": True,
                "text": "\n".join(
                    f"{index}. {case_line(case)}" for index, case in enumerate(top, start=1)
                ),
            },
        ]
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": body,
                    "actions": [{"type": "Action.OpenUrl", "title": "Avaa Kaista", "url": url}],
                },
            }
        ],
    }


def build_html(message: str, ific: str, url: str) -> str:
    """A standalone Teams-styled preview of the same message: no assets, no app/static/."""
    text = "\n".join(
        f"<p><b>{html.escape(line.lstrip('# '))}</b></p>"
        if line.startswith("#")
        else f"<p>{html.escape(line)}</p>"
        if line
        else ""
        for line in message.splitlines()
    )
    return f"""<!DOCTYPE html>
<html lang="fi">
<meta charset="utf-8">
<title>Teams-esikatselu — BR IFIC {html.escape(ific)}</title>
<body style="{_TEAMS_STYLE}">
<div style="{_CARD_STYLE}">
<b>Kaista-botti</b> <span style="color:#616161">· esikatselu</span>
{text}
<a href="{html.escape(url)}" style="display:inline-block;margin-top:8px;padding:6px 14px;
background:#5b5fc7;color:#fff;border-radius:4px;text-decoration:none">Avaa Kaista</a>
</div>
</body>
</html>
"""


def send(url: str, payload: dict) -> int:
    """POST the card to the webhook. Returns 0 on success, 1 on failure (no traceback)."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            print(f"Lähetetty: HTTP {response.status}")
    except urllib.error.HTTPError as error:
        print(f"Lähetys epäonnistui: HTTP {error.code}", file=sys.stderr)
        return 1
    except urllib.error.URLError as error:
        print(f"Lähetys epäonnistui: {error.reason}", file=sys.stderr)
        return 1
    return 0


def default_out() -> Path:
    """The digest reads the run the UI shows: KAISTA_OUT, else runs/latest, else out/."""
    pinned = os.environ.get("KAISTA_OUT")
    if pinned:
        return Path(pinned)
    latest = Path(__file__).resolve().parent.parent / "runs" / "latest"
    return latest if latest.is_dir() else Path("out")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Yksi Teams-digest per IFIC-ajo.")
    parser.add_argument("--dry-run", action="store_true", help="tulosta ja kirjoita tiedostot")
    parser.add_argument("--send", action="store_true", help="POSTaa TEAMS_WEBHOOK_URLiin")
    parser.add_argument("--html", action="store_true", help="kirjoita myös Teams-esikatselu")
    parser.add_argument("--out", default=default_out(), type=Path)
    parser.add_argument("--url", default=os.environ.get("KAISTA_URL", "http://localhost:8000"))
    args = parser.parse_args(argv)

    counts, cases = load(args.out)
    ific = ific_tag(cases)
    top = top_cases(cases)
    message = build_message(counts, top, ific, args.url)
    card = build_card(counts, top, ific, args.url)

    if args.dry_run or not args.send:
        print(message)
    if args.dry_run:
        (args.out / "teams_message.md").write_text(message + "\n", encoding="utf-8")
        (args.out / "teams_message.json").write_text(
            json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if args.html:
            (args.out / "teams_message.html").write_text(
                build_html(message, ific, args.url), encoding="utf-8"
            )
    if args.send:
        webhook = os.environ.get("TEAMS_WEBHOOK_URL")
        if not webhook:
            print("TEAMS_WEBHOOK_URL puuttuu: aseta se ennen --send.", file=sys.stderr)
            return 1
        return send(webhook, card)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

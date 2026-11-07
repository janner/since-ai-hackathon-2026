"""Task bodies for the IFIC triage Data Science Pipeline.

The pipeline has three container tasks, each running this module with one stage name:

    ingest   pull the published IFIC package and the two side inputs from the object
             store, and unpack the Access database the deterministic core reads
    triage   run the deterministic funnel (gates -> cards) with the served model's prose and
             the numeric guard, writing the run's output into /workspace/out
    metrics  read that output back and report the funnel numbers and the guard's rejection share

The stages share the workspace PVC and nothing else, so every number the last stage
reports comes from a file the earlier stages actually wrote.

    python -m pipeline_stages <stage>
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

WORKSPACE = Path(os.environ.get("KAISTA_WORKSPACE", "/workspace"))
S3_BASE = os.environ.get("KAISTA_S3_BASE", "").rstrip("/")
BUCKET = os.environ.get("KAISTA_S3_BUCKET", "ific")
_KEY_RE = re.compile(r"<Key>(.*?)</Key>")


def _list_keys(prefix: str = "") -> list[str]:
    """Object keys in the input bucket (anonymous read on that bucket).

    The response is the bucket we seeded ourselves, so a plain tag scan is enough
    and avoids pulling in an XML parser for one list call.
    """
    url = f"{S3_BASE}/{BUCKET}/?list-type=2&prefix={prefix}"
    with urllib.request.urlopen(url, timeout=60) as response:
        body = response.read().decode("utf-8", "replace")
    return _KEY_RE.findall(body)


def _get(key: str, target: Path) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{S3_BASE}/{BUCKET}/{key}", timeout=600) as response:
        target.write_bytes(response.read())
    return target.stat().st_size


def ingest() -> int:
    """Fetch the input objects into /workspace/in and unpack any package zip."""
    root = WORKSPACE / "in"
    keys = [k for k in _list_keys() if not k.endswith("/")]
    if not keys:
        print(f"error: bucket {BUCKET} at {S3_BASE} is empty", file=sys.stderr)
        return 2
    for key in sorted(keys):
        target = root / key
        print(f"ingest: {key} -> {target} ({_get(key, target)} B)")
        if target.suffix == ".zip":
            with zipfile.ZipFile(target) as archive:
                archive.extractall(root)  # names are sanitised by zipfile itself
                print(f"ingest: extracted {archive.namelist()} from {key}")

    mdbs = sorted(root.glob("*.mdb"))
    if len(mdbs) != 1:
        print(f"error: expected one .mdb under {root}, found {mdbs}", file=sys.stderr)
        return 2
    if shutil.which("mdb-export") is None:
        print("error: mdb-export missing from the task image", file=sys.stderr)
        return 2
    print(f"ingest: database {mdbs[0]} ({mdbs[0].stat().st_size} B), mdb-export present")
    return 0


def triage() -> int:
    """Run the funnel, the model's prose and the numeric guard over the workspace inputs."""
    from app.pipeline import run

    root = WORKSPACE / "in"
    database = sorted(root.glob("*.mdb"))[0]
    print(f"triage: database {database}")
    print(f"triage: model endpoint {os.environ.get('LLM_BASE_URL', '(unset)')}")
    return run(database, root / "register.csv", root / "m4.json", WORKSPACE / "out")


def metrics() -> int:
    """Report the funnel and the numeric guard's rejection share from the run's own output."""
    out = WORKSPACE / "out"
    funnel = json.loads((out / "funnel.json").read_text(encoding="utf-8"))
    cards = json.loads((out / "cases.json").read_text(encoding="utf-8"))

    counts = funnel["counts"]
    sources: dict[str, int] = {}
    for card in cards:
        source = card.get("prose", {}).get("source", "none")
        sources[source] = sources.get(source, 0) + 1
    drafted = sources.get("llm", 0) + sources.get("template_guard", 0)
    rejected = sources.get("template_guard", 0)
    share = rejected / drafted if drafted else 0.0

    summary = {
        "mode": funnel.get("mode", "slice"),
        "input_sha256": funnel.get("input_sha256", ""),
        "rules_version": funnel.get("rules_version", ""),
        "funnel": {
            "notices": counts["notices"],
            "g1": counts["g1"],
            "g2": counts["g2"],
            "g3": counts["g3"],
            "cannot_decide": counts["cannot_decide"],
        },
        "classes": {
            "exceeds": counts["exceeds"],
            "near": counts["near"],
            "clear": counts["clear"],
        },
        "queue_shown": funnel["queue"]["shown"],
        "prose_sources": sources,
        "guard": {
            "drafts_seen": drafted,
            "rejected": rejected,
            "rejection_share": round(share, 4),
        },
    }
    (out / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(
        f"metrics: {counts['notices']} notices → G1 {counts['g1']} → G2 {counts['g2']} → "
        f"G3 {counts['g3']} + {counts['cannot_decide']} cannot decide"
    )
    print(
        f"metrics: exceeds {counts['exceeds']}, near {counts['near']}, clear {counts['clear']}, "
        f"{funnel['queue']['shown']} in the queue"
    )
    print(f"metrics: prose sources {sources}")
    print(f"metrics: guard rejected {rejected}/{drafted} drafts, {share:.0%}")
    print("metrics: wrote /workspace/out/metrics.json")
    return 0


STAGES = {"ingest": ingest, "triage": triage, "metrics": metrics}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in STAGES:
        print(f"usage: python -m pipeline_stages [{'|'.join(STAGES)}]", file=sys.stderr)
        return 2
    return STAGES[argv[0]]()


if __name__ == "__main__":
    raise SystemExit(main())

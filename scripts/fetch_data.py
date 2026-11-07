"""Fetch the public input data into data/ and convert it to CSV.

Run from the repo root:  uv run python scripts/fetch_data.py
Needs `mdb-export` (apt install mdbtools). Data is never committed (see .gitignore).

1. ITU Space BR IFIC 3074 (zip -> mdb -> 15 CSV tables)
2. ITU terrestrial BR IFIC 3075 and 3076 (zip -> mdb, read by app/terrestrial.py)
3. Traficom open data, table of frequency allocations (Regulation M4 annex)
4. Traficom frequencies-of-interest xlsx -> CSV (copy the xlsx into data/ first;
   it is on the Since AI platform and is not redistributed here)
"""

import csv
import hashlib
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
IFIC_URL = "https://www.itu.int/sns/ific10/ific3074.zip"
TERR_URL = "https://www.itu.int/en/ITU-R/terrestrial/brific/BRIFIC/MDB/brific{}.zip"
TERR_NUMBERS = (3075, 3076)
M4_URL = "https://opendata.traficom.fi/api/v13/Taajuusjakotaulukko"
XLSX = "Traficom_SinceAI_Frequencies_of_interest_v05112026.xlsx"
TABLES = [
    "notice",
    "freq",
    "grp",
    "emiss",
    "s_beam",
    "geo",
    "non_geo",
    "orbit",
    "c_pfd",
    "srv_area",
    "srv_cls",
    "e_stn",
    "e_as_stn",
    "assgn",
    "ant_type",
]
UA = {"User-Agent": "Mozilla/5.0 (since-ai-2026 fetch_data)"}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()


def check_zip(body: bytes) -> bytes:
    # ITU answers a request without User-Agent with a 245-byte HTML page and status 200.
    if not body.startswith(b"PK"):
        raise SystemExit(f"IFIC download is not a zip ({len(body)} bytes, starts {body[:20]!r})")
    return body


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def xlsx_rows(path: Path):
    """Data rows under the English header row; the Finnish header row after it is skipped."""
    import openpyxl

    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    rows = iter(ws.iter_rows(values_only=True))
    for r in rows:
        if r and r[0] == "Station number":
            header = [c for c in r if c is not None]
            break
    else:
        raise SystemExit(f"{path.name}: header row 'Station number' not found")
    next(rows)  # Finnish headers
    yield header
    for r in rows:
        if r[0] is not None:
            yield ["" if c is None else c for c in r[: len(header)]]


def fetch_mdb(directory: Path, url: str, stem: str) -> tuple[Path, Path]:
    """Download a BR IFIC zip and extract its .mdb; returns (zip, mdb)."""
    directory.mkdir(parents=True, exist_ok=True)
    z = directory / f"{stem}.zip"
    if not z.exists():
        z.write_bytes(check_zip(get(url)))
    check_zip(z.read_bytes()[:2])
    with zipfile.ZipFile(z) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".mdb"))
        mdb = directory / Path(name).name
        if not mdb.exists():
            zf.extract(name, directory)
            (directory / name).rename(mdb)
    return z, mdb


def main():
    ific = DATA / "itu-ific-3074"
    z, mdb = fetch_mdb(ific, IFIC_URL, "ific3074")
    (ific / "csv").mkdir(parents=True, exist_ok=True)
    for t in TABLES:
        with (ific / "csv" / f"{t}.csv").open("w") as f:
            subprocess.run(["mdb-export", str(mdb), t], stdout=f, check=True)

    terrestrial = DATA / "itu-terr-ific"
    terr_files = [
        p for n in TERR_NUMBERS for p in fetch_mdb(terrestrial, TERR_URL.format(n), f"brific{n}")
    ]

    m4 = DATA / "taajuusjakotaulukko.json"
    if not m4.exists():
        m4.write_bytes(get(M4_URL))

    x = DATA / XLSX
    reg = DATA / "frequencies_of_interest.csv"
    if x.exists():
        with reg.open("w", newline="") as f:
            csv.writer(f).writerows(xlsx_rows(x))
    elif not reg.exists():
        print(
            f"MISSING: copy {XLSX} from the Since AI platform into {DATA}/ and run again.",
            file=sys.stderr,
        )

    for p in [z, mdb, *terr_files, m4, x, reg]:
        if p.exists():
            print(sha(p), p.relative_to(DATA.parent))


if __name__ == "__main__":
    main()

from pathlib import Path
from types import SimpleNamespace

import pytest

from app import gates, ingest, pfd
from app.bands import Band
from app.config import DEMO_SLICE_MHZ, SPACE_BANDS_MHZ
from app.territory import places as territory_places

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "rules" / "rr21_table21_4.csv"
DATA = ROOT / "data"
IFIC = DATA / "itu-ific-3074" / "ific3074.mdb"
REGISTER = DATA / "frequencies_of_interest.csv"
M4 = DATA / "taajuusjakotaulukko.json"


def pytest_collection_modifyitems(config, items):
    # The real challenge data is never committed: a clean clone runs green, data tests skip.
    if IFIC.is_file():
        return
    skip = pytest.mark.skip(reason="data/ missing: run scripts/fetch_data.py")
    for item in items:
        if "data" in item.keywords:
            item.add_marker(skip)


def _run_pipeline(ific_mdb: Path, register: Path, m4: Path, all_bands: bool) -> SimpleNamespace:
    """Load the BR IFIC MDB and run the gates once; the real data is too big to load per test."""
    ific = ingest.load_ific(ific_mdb)
    stations, counts = ingest.load_register(register)
    m4_rows = ingest.load_m4(m4)
    scope = SPACE_BANDS_MHZ if all_bands else (DEMO_SLICE_MHZ,)
    bands = [
        Band(lo_mhz=lo_mhz, hi_mhz=hi_mhz, group=index, stations=())
        for index, (lo_mhz, hi_mhz) in enumerate(scope)
    ]
    limits = pfd.load_limits(RULES)
    result = gates.run(
        ific,
        stations,
        list(territory_places()),
        bands,
        limits,
        m4_rows,
        mode="all" if all_bands else "slice",
    )
    return SimpleNamespace(
        ific=ific,
        stations=stations,
        counts=counts,
        bands=bands,
        limits=limits,
        result=result,
        m4=m4_rows,
    )


@pytest.fixture(scope="session")
def challenge() -> SimpleNamespace:
    """The real 3074 BR IFIC MDB, both the demo slice and all seven bands."""
    return SimpleNamespace(
        slice=_run_pipeline(IFIC, REGISTER, M4, False),
        all=_run_pipeline(IFIC, REGISTER, M4, True),
    )

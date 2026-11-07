from pathlib import Path
from types import SimpleNamespace

import pytest

from app import gates, ingest, pfd
from app.bands import derive_bands, select_bands, stations_on
from app.config import DEMO_SLICE_MHZ

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
    every_band = derive_bands(stations)
    bands = every_band if all_bands else select_bands(every_band, *DEMO_SLICE_MHZ)
    limits = pfd.load_limits(RULES)
    result = gates.run(
        ific,
        stations_on(stations, bands),
        bands,
        limits,
        mode="all" if all_bands else "slice",
    )
    return SimpleNamespace(
        ific=ific,
        stations=stations,
        counts=counts,
        bands=bands,
        all_bands=every_band,
        limits=limits,
        result=result,
        m4=ingest.load_m4(m4),
    )


@pytest.fixture(scope="session")
def challenge() -> SimpleNamespace:
    """The real 3074 BR IFIC MDB, both the demo slice and all seven bands."""
    return SimpleNamespace(
        slice=_run_pipeline(IFIC, REGISTER, M4, False),
        all=_run_pipeline(IFIC, REGISTER, M4, True),
    )

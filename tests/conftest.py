from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"


def pytest_collection_modifyitems(config, items):
    # Real challenge data is never committed: a clean clone runs green, data tests skip.
    if (DATA / "itu-ific-3074" / "csv").is_dir():
        return
    skip = pytest.mark.skip(reason="data/ missing: run scripts/fetch_data.py")
    for item in items:
        if "data" in item.keywords:
            item.add_marker(skip)

import importlib
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parent.parent / "data"


def test_package_imports():
    for name in ["app.main", "app.llm", "scripts.fetch_data"]:
        importlib.import_module(name)


@pytest.mark.data
def test_data_present():
    assert (DATA / "itu-ific-3074" / "ific3074.mdb").is_file()

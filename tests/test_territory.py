"""The territory edge and the Finnish allocation: the two inputs of the 7 Nov criterion."""

from app.allocation import finnish_bands, satellite_use
from app.config import M4_SUB_HI, M4_SUB_LO
from app.territory import Place, places


def test_the_edge_is_the_border_file_without_duplicates():
    edge = places()
    assert len(edge) == 552
    assert {point.section for point in edge} == {"SE", "NO", "RU", "TS"}
    assert all(isinstance(point, Place) for point in edge)
    assert edge[0].label == "land border, Sweden"
    assert any(point.label == "territorial sea outer limit" for point in edge)


def test_any_satellite_allocation_counts():
    assert satellite_use("FIXED SATELLITE (SPACE-TO-EARTH)")
    assert satellite_use("FIXED SATELLITE (EARTH-TO-SPACE)")  # uplink is still satellite use
    assert satellite_use("INTER-SATELLITE")
    assert satellite_use("Earth Exploration-Satellite")  # no direction named
    assert not satellite_use("MOBILE AND FIXED")
    assert not satellite_use("")


def test_the_allocation_is_merged_into_intervals():
    rows = [
        {M4_SUB_LO: 100, M4_SUB_HI: 200},
        {M4_SUB_LO: 150, M4_SUB_HI: 250},
        {M4_SUB_LO: 400, M4_SUB_HI: 500},
    ]
    assert finnish_bands(rows) == [(100 / 1e6, 250 / 1e6), (400 / 1e6, 500 / 1e6)]

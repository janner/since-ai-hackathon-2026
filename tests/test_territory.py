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


def test_satellite_use_means_a_space_to_earth_allocation():
    """The notices are downlinks: only a space-to-Earth (or undirected, or active) space
    allocation covers them. An uplink-only band is a finding for a downlink (D18)."""
    assert satellite_use("FIXED SATELLITE (SPACE-TO-EARTH)")
    assert satellite_use("BROADCASTING-SATELLITE")
    assert satellite_use("Earth Exploration-Satellite")  # no direction named
    assert satellite_use("SPACE OPERATION (SPACE-TO-EARTH, SPACE-TO-SPACE)")
    assert satellite_use("Space research (space-to-Earth)")
    assert satellite_use("EARTH EXPLORATION-SATELLITE (ACTIVE)")
    assert not satellite_use("FIXED SATELLITE (EARTH-TO-SPACE)")
    assert not satellite_use("INTER-SATELLITE")
    assert not satellite_use("SPACE RESEARCH (PASSIVE)")
    assert not satellite_use("MOBILE AND FIXED")
    assert not satellite_use("")


def test_the_allocation_is_merged_into_intervals():
    rows = [
        {M4_SUB_LO: 100, M4_SUB_HI: 200},
        {M4_SUB_LO: 150, M4_SUB_HI: 250},
        {M4_SUB_LO: 400, M4_SUB_HI: 500},
    ]
    assert finnish_bands(rows) == [(100 / 1e6, 250 / 1e6), (400 / 1e6, 500 / 1e6)]

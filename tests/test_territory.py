"""The territory edge and the Finnish allocation: the two inputs of the 7 Nov criterion."""

from app.allocation import space_to_earth
from app.territory import Place, places


def test_the_edge_is_the_border_file_without_duplicates():
    edge = places()
    assert len(edge) == 552
    assert {point.section for point in edge} == {"SE", "NO", "RU", "TS"}
    assert all(isinstance(point, Place) for point in edge)
    assert edge[0].label == "land border, Sweden"
    assert any(point.label == "territorial sea outer limit" for point in edge)


def test_a_downlink_needs_the_space_to_earth_direction():
    assert space_to_earth("FIXED SATELLITE (SPACE-TO-EARTH)")
    assert space_to_earth("Earth Exploration-Satellite")  # no direction named: both ways
    assert not space_to_earth("FIXED SATELLITE (EARTH-TO-SPACE)")
    assert not space_to_earth("INTER-SATELLITE")
    assert not space_to_earth("MOBILE AND FIXED")
    assert not space_to_earth("")

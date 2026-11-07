"""Bands: derived from the register, merged only where channels really touch."""

import pytest

from app import ingest
from app.bands import Band, derive_bands, groups, overlaps, select_bands, stations_on
from app.config import DEMO_SLICE_MHZ, SPACE_BANDS_MHZ


def _station(station_id: str, centre_mhz: float, bw_mhz: float) -> ingest.Station:
    return ingest.Station(
        id=station_id,
        licence="MVV",
        lat=60.0,
        lon=24.0,
        rx_mhz=centre_mhz,
        tx_mhz=None,
        bw_mhz=bw_mhz,
        gain_db=None,
        power_w=None,
        direction_deg=None,
        ant_asl_m=None,
        ground_m=None,
    )


def test_overlaps_rejects_touching_bands():
    assert overlaps(100.0, 200.0, 150.0, 250.0)
    assert not overlaps(100.0, 200.0, 200.0, 300.0)


def test_derive_bands_merges_touching_channels_but_not_the_hole():
    # Two 100 MHz channels with a 100 MHz hole between them: two bands, one allocation.
    bands = derive_bands([_station("1", 3500.0, 100.0), _station("2", 3700.0, 100.0)])
    assert [(b.lo_mhz, b.hi_mhz) for b in bands] == [(3450.0, 3550.0), (3650.0, 3750.0)]
    assert groups(bands) == 1
    assert [b for b in bands if overlaps(b.lo_mhz, b.hi_mhz, 3550.0, 3650.0)] == []


def test_zero_bandwidth_is_a_point_not_a_crash():
    bands = derive_bands([_station("1", 3550.0, 0.0)])
    assert [(b.lo_mhz, b.hi_mhz) for b in bands] == [(3550.0, 3550.0)]


def test_channels_that_touch_become_one_band():
    bands = derive_bands([_station("1", 3500.0, 100.0), _station("2", 3600.0, 100.0)])
    assert [(b.lo_mhz, b.hi_mhz, b.stations) for b in bands] == [(3450.0, 3650.0, ("1", "2"))]


def test_select_bands_is_the_demo_slice():
    in_slice = _station("1", 3600.0, 100.0)  # 3 550-3 650 MHz, inside the demo slice
    next_band = _station("2", 6100.0, 100.0)  # 6 050-6 150 MHz, the next space allocation
    every = derive_bands([in_slice, next_band])
    assert len(every) == 2
    assert [b.stations for b in select_bands(every, *DEMO_SLICE_MHZ)] == [("1",)]
    assert len(SPACE_BANDS_MHZ) == 7


def test_stations_on_band_uses_register_order():
    stations = [
        _station("3000", 3600.0, 100.0),
        _station("1000", 3500.0, 100.0),
        _station("9000", 100.0, 100.0),  # outside every space allocation
    ]
    bands = derive_bands(stations)
    assert [s.id for s in stations_on(stations, bands)] == ["3000", "1000"]


def test_band_stations_are_recorded():
    band = Band(lo_mhz=100.0, hi_mhz=200.0, group=0, stations=("1", "2"))
    assert band.width_mhz == 100.0
    assert band.stations == ("1", "2")


@pytest.mark.data
def test_real_band_derivation(challenge):
    assert challenge.all.counts["stations"] == 871
    assert len(challenge.all.bands) == 26
    assert groups(challenge.all.bands) == 7
    assert len(challenge.slice.bands) == 2  # the 13,1 MHz hole is not protected
    on_band = stations_on(challenge.slice.stations, challenge.slice.bands)
    assert len(on_band) == 7
    # Register order, which is not frequency order.
    assert sorted(s.id for s in on_band) == [
        "981340",
        "983254",
        "983816",
        "985407",
        "986805",
        "987028",
        "989011",
    ]
    for station in on_band:
        assert station.bw_mhz == 100.0


@pytest.mark.data
def test_real_bands_cover_the_register_rows(challenge):
    covered = {sid for band in challenge.all.bands for sid in band.stations}
    assert len(covered) == 84

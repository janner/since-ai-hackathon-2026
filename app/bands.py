"""Derive the protected bands from the Finnish register.

No channel frequency is hardcoded: a protected band comes from a register row whose
channel overlaps one of the seven space allocations in app.config.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import SPACE_BANDS_MHZ
from app.ingest import Station

# Channels that overlap or touch form one protected band. Nothing is joined across a real
# hole: the register leaves a 13.1 MHz gap inside the demo slice (3 663.7-3 676.8 MHz), and
# the tool shows that gap instead of claiming protection the register does not declare.
MERGE_GAP_MHZ = 0.0


@dataclass(frozen=True)
class Band:
    lo_mhz: float
    hi_mhz: float
    group: int
    stations: tuple[str, ...]

    @property
    def width_mhz(self) -> float:
        return self.hi_mhz - self.lo_mhz


def overlaps(lo_a: float, hi_a: float, lo_b: float, hi_b: float) -> bool:
    return lo_a < hi_b and hi_a > lo_b


def derive_bands(stations: list[Station]) -> list[Band]:
    """One merged band per protected region, per space allocation."""
    bands: list[Band] = []
    for group, (lo_mhz, hi_mhz) in enumerate(SPACE_BANDS_MHZ):
        hits = [s for s in stations if overlaps(s.lo_mhz, s.hi_mhz, lo_mhz, hi_mhz)]
        bands.extend(_merge(hits, group))
    return bands


def _merge(hits: list[Station], group: int) -> list[Band]:
    bands: list[Band] = []
    for station in sorted(hits, key=lambda s: s.lo_mhz):
        last = bands[-1] if bands else None
        if last is not None and station.lo_mhz - last.hi_mhz <= MERGE_GAP_MHZ:
            bands[-1] = Band(
                lo_mhz=last.lo_mhz,
                hi_mhz=max(last.hi_mhz, station.hi_mhz),
                group=group,
                stations=last.stations + (station.id,),
            )
        else:
            bands.append(
                Band(
                    lo_mhz=station.lo_mhz,
                    hi_mhz=station.hi_mhz,
                    group=group,
                    stations=(station.id,),
                )
            )
    return bands


def select_bands(bands: list[Band], lo_mhz: float, hi_mhz: float) -> list[Band]:
    return [b for b in bands if overlaps(b.lo_mhz, b.hi_mhz, lo_mhz, hi_mhz)]


def station_ids(bands: list[Band]) -> list[str]:
    return sorted({sid for band in bands for sid in band.stations})


def stations_on(stations: list[Station], bands: list[Band]) -> list[Station]:
    """Register rows that overlap the selected bands, in register order."""
    return [
        s for s in stations if any(overlaps(s.lo_mhz, s.hi_mhz, b.lo_mhz, b.hi_mhz) for b in bands)
    ]


def groups(bands: list[Band]) -> int:
    """How many of the seven allocations actually protect something."""
    return len({band.group for band in bands})

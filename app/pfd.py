"""Geometry and the ITU RR Art. 21 Table 21-4 PFD limit.

Every number here is either a physical constant, a formula, or a row read from
rules/rr21_table21_4.csv. No limit is hardcoded in code.
A service-scoped row is applied to every downlink in its band: conservative, never under-protects.
"""

from __future__ import annotations

import bisect
import csv
import math
from dataclasses import dataclass
from pathlib import Path

from app.config import fmt_mhz

RE_KM = 6378.137  # Earth radius used by the reference calculation
GEO_KM = 42164.0  # nominal geostationary radius
GEO_R = GEO_KM / RE_KM


@dataclass(frozen=True)
class LimitRow:
    freq_lo_mhz: float
    freq_hi_mhz: float
    orbit: str  # GSO, NGSO, HEO or any
    a_db: float
    k_db: float
    ref_hz: float
    offset: str  # '', 'X' or 'Y'
    service: str
    page: str
    source: str
    breaks: tuple[tuple[float, ...], ...] = ()  # piecewise-linear (deg, dB in ref_hz) points

    def cite(self) -> str:
        return (
            f"{self.source}, {fmt_mhz(self.freq_lo_mhz)}-{fmt_mhz(self.freq_hi_mhz)} MHz, "
            f"{self.service}, {self.orbit}, {self.page}"
        )


def load_limits(path: Path) -> list[LimitRow]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            LimitRow(
                freq_lo_mhz=float(row["freq_lo_mhz"]),
                freq_hi_mhz=float(row["freq_hi_mhz"]),
                orbit=row["orbit"].strip(),
                a_db=float(row["a_db"]),
                k_db=float(row["k_db"]),
                ref_hz=float(row["ref_hz"]),
                offset=row["offset"].strip(),
                service=row["service"].strip(),
                page=row["page"].strip(),
                source=row["source"].strip(),
                breaks=tuple(
                    tuple(float(v) for v in point.split(":"))
                    for point in (row.get("breaks") or "").split(";")
                    if point.strip()
                ),
            )
            for row in csv.DictReader(handle)
        ]
    for row in rows:
        degs = [d for d, _ in row.breaks]
        if row.breaks and (row.offset or degs != sorted(set(degs)) or degs[0] > 0 or degs[-1] < 90):
            raise ValueError(f"bad breaks row: {row}")  # breaks carry no X/Y offset, span 0-90
    return rows


def limit_row(limits: list[LimitRow], lo_mhz: float, hi_mhz: float, orbit: str) -> LimitRow | None:
    """The strictest row of this orbit class over the notified band, or None for
    `no_limit_for_band` when any part of the band has no row. HEO takes an NGSO row only
    where the table gives HEO no row of its own."""

    def applies(row: LimitRow) -> bool:
        if row.orbit in (orbit, "any"):
            return True
        if orbit != "HEO" or row.orbit != "NGSO":
            return False
        return not any(
            r.orbit == "HEO" and _overlaps(r, row.freq_lo_mhz, row.freq_hi_mhz) for r in limits
        )

    rows = sorted(
        (r for r in limits if applies(r) and _overlaps(r, lo_mhz, hi_mhz)),
        key=lambda r: r.freq_lo_mhz,
    )
    covered = lo_mhz
    for row in rows:
        if row.freq_lo_mhz > covered:
            return None  # a gap between rows: part of the band has no limit
        covered = max(covered, row.freq_hi_mhz)
    if not rows or covered < hi_mhz:
        return None
    return min(rows, key=lambda r: (limit_hz(r, 0.0), limit_hz(r, 90.0)))


def _overlaps(row: LimitRow, lo_mhz: float, hi_mhz: float) -> bool:
    """Strict overlap (a touching edge is not overlap), or containment for a point band."""
    contains = row.freq_lo_mhz <= lo_mhz and hi_mhz <= row.freq_hi_mhz
    return contains or (row.freq_lo_mhz < hi_mhz and row.freq_hi_mhz > lo_mhz)


def limit_hz(row: LimitRow, elev_deg: float, offset_db: float = 0.0) -> float:
    """PFD limit in dB(W/m2/Hz) at an elevation angle. Continuous at 25 deg."""
    if row.breaks:
        degs = [d for d, _ in row.breaks]
        i = min(max(bisect.bisect_right(degs, elev_deg), 1), len(degs) - 1)
        (d0, v0), (d1, v1) = row.breaks[i - 1], row.breaks[i]
        value = v0 + (v1 - v0) * (min(max(elev_deg, d0), d1) - d0) / (d1 - d0)
        return value - 10 * math.log10(row.ref_hz)
    if elev_deg <= 5:
        value = row.a_db - offset_db
    elif elev_deg <= 25:
        value = row.a_db - offset_db + (row.k_db + offset_db) * (elev_deg - 5) / 20
    else:
        value = row.a_db + row.k_db
    return value - 10 * math.log10(row.ref_hz)


def look(lat: float, lon: float, sat_lon: float) -> tuple[float, float]:
    """GEO: elevation in degrees and slant range in km from a station to a satellite."""
    delta = math.radians(sat_lon - lon)
    phi = math.radians(lat)
    cos_g = max(-1.0, min(1.0, math.cos(phi) * math.cos(delta)))
    central = math.acos(cos_g)
    distance = math.sqrt(RE_KM**2 + GEO_KM**2 - 2 * RE_KM * GEO_KM * cos_g)
    sin_g = math.sin(central) or 1e-9
    elevation = math.degrees(math.atan2(cos_g - 1 / GEO_R, sin_g))
    return elevation, distance


def slant(h_km: float, elev_deg: float) -> float:
    """non-GSO: slant range in km from an altitude at an elevation angle."""
    e = math.radians(elev_deg)
    return math.sqrt((RE_KM + h_km) ** 2 - (RE_KM * math.cos(e)) ** 2) - RE_KM * math.sin(e)


def fspl(d_km: float) -> float:
    return 10 * math.log10(4 * math.pi * (d_km * 1000) ** 2)


def x_fn(n: int) -> float | None:
    """Footnote 13 offset. None when N >= 1000: it would need Nv, which IFIC does not give."""
    if n <= 50:
        return 0.0
    if n <= 288:
        return 5 / 119 * (n - 50)
    if n <= 999:
        return (n + 402) / 69
    return None


def y_fn(n_max: int) -> float:
    """Footnote 22 offset: Y = 5 log(max(NN, NS)), applied when max > 2."""
    return 0.0 if n_max <= 2 else 5 * math.log10(n_max)


def ngso_reach(orbit) -> float:
    """Highest latitude a satellite on this orbit row reaches at zero elevation."""
    if orbit.inclin_ang is None or orbit.apog_km is None:
        return 90.0  # unknown orbit: never claim it is out of reach, let G3 decide
    inclination, apogee = orbit.inclin_ang, orbit.apog_km
    return min(inclination, 180 - inclination) + math.degrees(math.acos(RE_KM / (RE_KM + apogee)))


def is_heo(orbits) -> bool:
    """Highly elliptical: apogee above 18 000 km and a steep inclination (footnote 24)."""
    return any((o.apog_km or 0) > 18000 and 35 <= (o.inclin_ang or 0) <= 145 for o in orbits)

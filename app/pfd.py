"""Geometry and the ITU RR Art. 21 Table 21-4 PFD limit.

Every number here is either a physical constant, a formula, or a row read from
rules/rr21_table21_4.csv. No limit is hardcoded in code.

A notified band is split at the table's row edges and every part is computed against the rows
that cover it. Where several rows cover the same part, the worst margin over all of them is
reported; where no row covers a part, the part is a gap in the table and the case never reads
`clear`.
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

# A footnote whose limit cannot be computed from the IFIC fields: the footnote's condition
# (a SAR formula, a resolution's own PFD) is the limit, not an a/k pair. The reason code names
# the footnote so the card can point at the text instead of saying "no limit".
UNCOMPUTABLE_FOOTNOTES = {
    "18": "footnote_18_eess_active",  # 9.9-10.4 GHz EESS (active), SAR formula in footnote 18
    "26": "footnote_26_ngso_iss",  # 27.5-30 GHz ISS, Resolution 679 in footnote 26
}


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
    region: str = ""  # "all", "Region 1", "Regions 1 and 3"
    footnotes: str = ""  # "13", "7; 8; 14; 15", "18"
    breakpoints: tuple[tuple[float, float], ...] = ()  # (deg, dB in ref_hz), piecewise linear

    def cite(self) -> str:
        text = (
            f"{self.source}, {fmt_mhz(self.freq_lo_mhz)}-{fmt_mhz(self.freq_hi_mhz)} MHz, "
            f"{self.service}, {self.orbit}, {self.page}"
        )
        if self.footnotes:
            text += f", footnotes {self.footnotes}"
        return text


@dataclass(frozen=True)
class LimitSegment:
    """One contiguous part of a notified band and the table rows that cover it."""

    freq_lo_mhz: float
    freq_hi_mhz: float
    rows: tuple[LimitRow, ...]  # empty: RR Table 21-4 gives no PFD limit on this part

    @property
    def covered(self) -> bool:
        return bool(self.rows)


def _parse_breakpoints(text: str) -> tuple[tuple[float, float], ...]:
    """'0:-113;5.7:-113;6:-109.00' -> ((0, -113), (5.7, -113), (6, -109.0))."""
    points: list[tuple[float, float]] = []
    for part in text.replace("|", ";").split(";"):
        part = part.strip()
        if not part:
            continue
        separator = "=" if "=" in part else ":"
        key, _, value = part.partition(separator)
        points.append((float(key.strip().replace(",", ".")), float(value.strip().replace(",", "."))))
    return tuple(points)


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
                region=(row.get("region") or "").strip(),
                footnotes=(row.get("footnotes") or "").strip(),
                breakpoints=_parse_breakpoints(row.get("breakpoints") or ""),
            )
            for row in csv.DictReader(handle)
        ]
    for row in rows:
        degs = [deg for deg, _ in row.breakpoints]
        if row.breakpoints and (row.offset or degs != sorted(set(degs)) or degs[0] > 0 or degs[-1] < 90):
            raise ValueError(f"bad breakpoints row: {row}")  # no X/Y offset, spans 0-90 deg
    return rows


def _overlaps(row: LimitRow, lo_mhz: float, hi_mhz: float) -> bool:
    """Strict overlap (a touching edge is not overlap), or containment for a point band."""
    contains = row.freq_lo_mhz <= lo_mhz and hi_mhz <= row.freq_hi_mhz
    return contains or (row.freq_lo_mhz < hi_mhz and row.freq_hi_mhz > lo_mhz)


def _applies(row: LimitRow, orbit: str, limits: list[LimitRow]) -> bool:
    """Whether the row's orbit class covers this notice. HEO falls back to NGSO only where the
    table gives HEO no row of its own on the same band."""
    if row.orbit in (orbit, "any"):
        return True
    if orbit != "HEO" or row.orbit != "NGSO":
        return False
    return not any(
        other.orbit == "HEO" and _overlaps(other, row.freq_lo_mhz, row.freq_hi_mhz) for other in limits
    )


def limit_segments(
    limits: list[LimitRow], lo_mhz: float, hi_mhz: float, orbit: str
) -> list[LimitSegment]:
    """Split [lo, hi] at every table row edge and name the rows that cover each part.

    A band that crosses a row edge is computed part by part on its own row. A part no row
    covers is returned with an empty `rows` tuple: the caller records the fact "RR Table 21-4
    gives no PFD limit for X-Y MHz" and never lets the case read `clear`.
    """
    if hi_mhz < lo_mhz:
        lo_mhz, hi_mhz = hi_mhz, lo_mhz
    applicable = [row for row in limits if _applies(row, orbit, limits)]
    edges = {lo_mhz, hi_mhz}
    for row in applicable:
        if lo_mhz < row.freq_lo_mhz < hi_mhz:
            edges.add(row.freq_lo_mhz)
        if lo_mhz < row.freq_hi_mhz < hi_mhz:
            edges.add(row.freq_hi_mhz)
    ordered = sorted(edges)
    segments: list[LimitSegment] = []
    for low, high in zip(ordered, ordered[1:]):
        if high <= low:
            continue
        covering = tuple(
            row for row in applicable if row.freq_lo_mhz <= low and high <= row.freq_hi_mhz
        )
        segments.append(LimitSegment(low, high, covering))
    if not segments:
        segments.append(LimitSegment(lo_mhz, hi_mhz, ()))
    return segments


def limit_row(limits: list[LimitRow], lo_mhz: float, hi_mhz: float, orbit: str) -> LimitRow | None:
    """The single row that contains the whole notified band, or None when no one row does.

    Kept as the narrow helper the older tests use; the gates walk `limit_segments` so a band
    that crosses a row edge is computed part by part instead of being refused whole.
    """
    for row in limits:
        if not (lo_mhz >= row.freq_lo_mhz and hi_mhz <= row.freq_hi_mhz):
            continue
        if _applies(row, orbit, limits):
            return row
    return None


def footnote_codes(row: LimitRow) -> list[str]:
    """The numeric footnote codes on a row, in order, without the 'No.' entries."""
    codes: list[str] = []
    for part in row.footnotes.replace(",", ";").split(";"):
        code = part.strip().replace("footnote", "").strip()
        if code.isdigit():
            codes.append(code)
    return codes


def uncomputable_reason(row: LimitRow) -> str | None:
    """The reason code when this row's limit is a footnote formula, not an a/k pair."""
    for code in footnote_codes(row):
        if code in UNCOMPUTABLE_FOOTNOTES:
            return UNCOMPUTABLE_FOOTNOTES[code]
    return None


def x_missing_reason(row: LimitRow) -> str:
    """The reason code when an X-offset row needs Nv and the IFIC row gives N >= 1000.

    Footnote 13 is the X offset; the row also carries footnotes 7 and 8 for its service
    conditions. The code names 13 when present so the card points at the right text.
    """
    codes = footnote_codes(row)
    if "13" in codes:
        return "footnote_13_nv_missing"
    return f"footnote_{codes[0]}_nv_missing" if codes else "x_needs_nv"


def no_agreed_limit_reason(low_mhz: float, high_mhz: float) -> str:
    """The fact a gap leaves: RR Table 21-4 gives no PFD limit on this interval."""
    return (
        f"no_agreed_limit: RR Table 21-4 gives no PFD limit for "
        f"{fmt_mhz(low_mhz)}-{fmt_mhz(high_mhz)} MHz"
    )


def limit_hz(row: LimitRow, elev_deg: float, offset_db: float = 0.0) -> float:
    """PFD limit in dB(W/m2/Hz) at an elevation angle. Continuous at 25 deg.

    A row with `breakpoints` is a piecewise-linear curve read from the table; the points are
    absolute limits in the reference bandwidth and carry no X/Y offset. A row without them uses
    the table's a/k formula.
    """
    if row.breakpoints:
        degs = [deg for deg, _ in row.breakpoints]
        index = min(max(bisect.bisect_right(degs, elev_deg), 1), len(degs) - 1)
        (deg0, value0), (deg1, value1) = row.breakpoints[index - 1], row.breakpoints[index]
        clamped = min(max(elev_deg, deg0), deg1)
        value = value0 + (value1 - value0) * (clamped - deg0) / (deg1 - deg0)
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

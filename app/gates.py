"""G1-G4: the funnel that turns 196 notices into a queue of cases.

Deterministic by construction: no LLM, no network, no clock except the run timestamp.
Every dropped notice leaves with a reason code, including the ones dropped in the first gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app import pfd
from app.bands import Band
from app.config import EXCEEDS_DB, NEAR_DB
from app.ingest import Freq, IficData, Station

CLASS_ORDER = ("exceeds", "near", "cannot_decide", "clear")
STAGES = ("G1", "G2")


def classify(margin_db: float) -> str:
    if margin_db > EXCEEDS_DB:
        return "exceeds"
    return "near" if margin_db > NEAR_DB else "clear"


@dataclass(frozen=True)
class Case:
    """One notice with a computed worst case."""

    ntc_id: str
    orbit: str
    beam: str
    grp_id: str
    band_lo_mhz: float
    band_hi_mhz: float
    victim: Station
    elev_deg: float
    slant_km: float
    psd_dbw_hz: float
    beam_gain_db: float
    eirp_dbw_hz: float
    fspl_db: float
    pfd_dbw_m2_hz: float
    limit_dbw_m2_hz: float
    margin_db: float
    offset_db: float
    perigee_km: float | None
    limit: pfd.LimitRow
    klass: str


@dataclass(frozen=True)
class QueueItem:
    """A row in the queue: a computed case or a notice that cannot be decided."""

    ntc_id: str
    klass: str
    reason: str
    margin_db: float | None
    case: Case | None = None


@dataclass
class GateResult:
    cases: list[Case]
    undecided: dict[str, str]  # ntc_id -> reason (cannot_decide)
    dropped: dict[str, tuple[str, str]]  # ntc_id -> (stage, reason)
    queue: list[QueueItem] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    drops: dict[str, int] = field(default_factory=dict)
    stations_on_band: int = 0
    stations: list[Station] = field(default_factory=list)
    bands: list[Band] = field(default_factory=list)
    geo_visible: int = 0
    ngso_visible: int = 0
    mode: str = "slice"
    run_at: str = ""
    input_sha256: str = ""
    rules_version: str = ""
    freq_rows: int = 0
    elapsed_s: float = 0.0

    def case_by_id(self) -> dict[str, Case]:
        return {case.ntc_id: case for case in self.cases}

    def reason_counts(self, stage: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for dropped_stage, reason in self.dropped.values():
            if dropped_stage == stage:
                counts[reason] = counts.get(reason, 0) + 1
        return counts


def run(
    ific: IficData,
    stations: list[Station],
    bands: list[Band],
    limits: list[pfd.LimitRow],
    mode: str = "slice",
) -> GateResult:
    found, g1_dropped = gate1(ific, bands)
    visible, g2_dropped = gate2(ific, found, stations)
    cases, undecided = gate3(ific, visible, stations, limits)
    cases.sort(key=lambda case: -case.margin_db)
    dropped = {**g1_dropped, **g2_dropped}
    queue = gate4(cases, undecided)

    counts = {
        "notices": len(ific.notices),
        "g1": len(found),
        "g2": len(visible),
        "g3": len(cases),
        "cannot_decide": len(undecided),
    }
    for klass in ("exceeds", "near", "clear"):
        counts[klass] = sum(1 for case in cases if case.klass == klass)

    result = GateResult(
        cases=cases,
        undecided=undecided,
        dropped=dropped,
        queue=queue,
        counts=counts,
        stations_on_band=len(stations),
        stations=stations,
        bands=bands,
        geo_visible=sum(1 for ntc_id in visible if ntc_id in ific.geo),
        ngso_visible=sum(1 for ntc_id in visible if ntc_id not in ific.geo),
        mode=mode,
        input_sha256=ific.input_sha256,
    )
    result.drops = {**result.reason_counts("G1"), **result.reason_counts("G2")}
    return result


def gate1(ific: IficData, bands: list[Band]) -> tuple[dict[str, list[Freq]], dict]:
    """Do the notice's space-to-Earth rows overlap a protected band?"""
    wanted = [(band.lo_mhz, band.hi_mhz) for band in bands]
    found: dict[str, list[Freq]] = {}
    for freq in ific.freqs:
        if freq.emi_rcp != "E":
            continue
        if not any(freq.freq_min_mhz <= hi and freq.freq_max_mhz >= lo for lo, hi in wanted):
            continue
        found.setdefault(freq.ntc_id, []).append(freq)

    earth_notices = {n for n in found if ific.notices[n].ntc_type == "S"}
    for ntc_id in earth_notices:
        # An earth station notice sending "E" is the station transmitting, not a downlink.
        del found[ntc_id]

    dropped: dict[str, tuple[str, str]] = {}
    for ntc_id in ific.notices:
        if ntc_id in found:
            continue
        reason = "earth_station_notice" if ntc_id in earth_notices else "no_band_overlap"
        dropped[ntc_id] = ("G1", reason)
    return found, dropped


def gate2(
    ific: IficData, found: dict[str, list[Freq]], stations: list[Station]
) -> tuple[dict[str, list[Freq]], dict[str, tuple[str, str]]]:
    """Is the satellite visible from Finland at all?"""
    visible: dict[str, list[Freq]] = {}
    dropped: dict[str, tuple[str, str]] = {}
    lat_min = min(abs(station.lat) for station in stations)
    for ntc_id, freqs in found.items():
        geo = ific.geo.get(ntc_id)
        if geo is not None and geo.long_nom is not None:
            top = max(pfd.look(s.lat, s.lon, geo.long_nom)[0] for s in stations)
            if top <= 0:
                dropped[ntc_id] = ("G2", "geo_below_horizon")
                continue
        else:
            orbits = ific.orbits.get(ntc_id)
            if orbits and max(pfd.ngso_reach(orbit) for orbit in orbits) < lat_min:
                dropped[ntc_id] = ("G2", "ngso_never_visible")
                continue
        visible[ntc_id] = freqs
    return visible, dropped


def gate3(
    ific: IficData,
    visible: dict[str, list[Freq]],
    stations: list[Station],
    limits: list[pfd.LimitRow],
) -> tuple[list[Case], dict[str, str]]:
    """Worst-case PFD against the Table 21-4 limit, per notice."""
    cases: list[Case] = []
    undecided: dict[str, str] = {}
    for ntc_id, freqs in visible.items():
        worst, missing = _worst_for_notice(ific, ntc_id, freqs, stations, limits)
        if worst is None:
            undecided[ntc_id] = missing or "no_station"
        else:
            cases.append(worst)
    return cases, undecided


def _worst_for_notice(
    ific: IficData,
    ntc_id: str,
    freqs: list[Freq],
    stations: list[Station],
    limits: list[pfd.LimitRow],
) -> tuple[Case | None, str | None]:
    geo = ific.geo.get(ntc_id)
    sat_lon = geo.long_nom if geo is not None else None
    geostationary = sat_lon is not None
    orbits = ific.orbits.get(ntc_id)
    perigee = None
    counts = (0, 0)  # nbr_sat_nh, nbr_sat_sh
    if geostationary:
        orbit = "GSO"
    else:
        if not orbits:
            return None, "no_orbit"
        orbit = "HEO" if pfd.is_heo(orbits) else "NGSO"
        real_perigees = [o.perig_km for o in orbits if o.perig_km is not None]
        if not real_perigees:
            return None, "no_perigee"  # a missing perigee must not read as far away and clear
        perigee = min(real_perigees)
        nongeo = ific.nongeo.get(ntc_id)
        if nongeo is not None:
            counts = (nongeo.nbr_sat_nh, nongeo.nbr_sat_sh)
    worst: Case | None = None
    missing: str | None = None
    for freq in freqs:
        limit = pfd.limit_row(limits, freq.freq_min_mhz, freq.freq_max_mhz, orbit)
        if limit is None:
            missing = missing or "no_limit_for_band"
            continue
        psd = ific.emiss.get(freq.grp_id)
        if psd is None:
            missing = "no_power"
            continue
        gain = _beam_gain(ific, freq)
        if gain is None:
            missing = "no_gain"
            continue
        victims = [
            s
            for s in stations
            if not (s.hi_mhz < freq.freq_min_mhz or s.lo_mhz > freq.freq_max_mhz)
        ]
        if not victims:
            continue
        offset = 0.0
        if limit.offset == "Y":
            offset = pfd.y_fn(max(counts))
        elif limit.offset == "X":
            x_value = pfd.x_fn(sum(counts))
            if x_value is None:
                missing = "x_needs_nv"
                continue
            offset = x_value

        if sat_lon is not None:
            points = [(s, *pfd.look(s.lat, s.lon, sat_lon)) for s in victims]
        else:
            # shortcut: a non-GSO pass sweeps every latitude, so position does not change the
            # geometry; the pass is sampled from 0 to 90 deg in 0.1 deg steps. Upgrade if a real
            # orbit ephemeris ever arrives.
            points = [(victims[0], e / 10, pfd.slant(perigee, e / 10)) for e in range(901)]
        for station, elevation, distance in points:
            if elevation <= 0:
                continue
            level = psd + gain - pfd.fspl(distance)
            limit_db = pfd.limit_hz(limit, elevation, offset)
            margin = round(level - limit_db, 2)
            if worst is not None and margin <= worst.margin_db:
                continue
            worst = Case(
                ntc_id=ntc_id,
                orbit=orbit,
                beam=freq.beam_name,
                grp_id=freq.grp_id,
                band_lo_mhz=freq.freq_min_mhz,
                band_hi_mhz=freq.freq_max_mhz,
                victim=station,
                elev_deg=round(elevation, 2),
                slant_km=round(distance),
                psd_dbw_hz=round(psd, 2),
                beam_gain_db=round(gain, 2),
                eirp_dbw_hz=round(psd + gain, 2),
                fspl_db=round(pfd.fspl(distance), 2),
                pfd_dbw_m2_hz=round(level, 2),
                limit_dbw_m2_hz=round(limit_db, 2),
                margin_db=margin,
                offset_db=round(offset, 2),
                perigee_km=perigee,
                limit=limit,
                klass=classify(margin),
            )
    return worst, missing


def _beam_gain(ific: IficData, freq: Freq) -> float | None:
    """Max beam gain over the beams that cover the notified band (dBi)."""
    candidates = [
        beam.gain_db
        for beam in ific.beams.get((freq.ntc_id, freq.beam_name), [])
        if beam.gain_db is not None
        and beam.freq_min_mhz is not None
        and beam.freq_max_mhz is not None
        and beam.freq_min_mhz <= freq.freq_max_mhz
        and beam.freq_max_mhz >= freq.freq_min_mhz
    ]
    return max(candidates) if candidates else None


def gate4(cases: list[Case], undecided: dict[str, str]) -> list[QueueItem]:
    """Queue every concern, in class order then margin descending; clear stays out.

    No cap: the challenge brief names no target number, so nothing is cut.
    """
    items = [
        QueueItem(c.ntc_id, c.klass, c.klass, c.margin_db, c) for c in cases if c.klass != "clear"
    ]
    items += [
        QueueItem(ntc_id, "cannot_decide", reason, None) for ntc_id, reason in undecided.items()
    ]
    queue: list[QueueItem] = []
    for klass in CLASS_ORDER:
        same = [item for item in items if item.klass == klass]
        queue += sorted(same, key=lambda item: (-(item.margin_db or 0.0), item.ntc_id))
    return queue

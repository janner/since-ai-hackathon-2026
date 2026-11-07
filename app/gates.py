"""G1-G4: the funnel that turns 196 notices into a queue of cases.

Deterministic by construction: no LLM, no network, no clock except the run timestamp.
Every dropped notice leaves with a reason code, including the ones dropped in the first gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app import allocation, config, pfd
from app.bands import Band
from app.config import EXCEEDS_DB, NEAR_DB
from app.ingest import Freq, IficData, Notice, Station
from app.territory import Place

CLASS_ORDER = ("exceeds", "near", "not_space", "cannot_decide")
STAGES = ("G1", "G2")


def classify(margin_db: float, adjacent: bool = False, band_space: bool = True) -> str:
    """exceeds above 0 dB, near above -3 dB, not_space on a band Finland does not use for
    satellite downlinks, clear otherwise.

    An adjacent-channel case is capped at `near`: the Table 21-4 limit is a property of the
    notified band and does not apply outside it, so a guard-only case must not read as `exceeds`.
    """
    if margin_db > EXCEEDS_DB:
        klass = "exceeds"
    elif margin_db > NEAR_DB:
        klass = "near"
    elif not band_space:
        klass = "not_space"
    else:
        klass = "clear"
    return "near" if adjacent and klass == "exceeds" else klass


@dataclass(frozen=True)
class Case:
    """One notice with a computed worst case over Finnish territory."""

    ntc_id: str
    orbit: str
    beam: str
    grp_id: str
    band_lo_mhz: float
    band_hi_mhz: float
    victim: Station | None  # the worst reference row on the band, when the register has one
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
    band_space: bool
    band_use: str
    adjacent: bool = False
    lat: float | None = None
    lon: float | None = None
    place: str = ""  # where the level was computed; "" for a non-GSO pass
    deadline: date | None = None  # the notice's Resolution 35 deadline, from grp_res35
    deadline_passed: bool = False  # that deadline is already behind the run


@dataclass(frozen=True)
class QueueItem:
    """A row in the queue: a computed case or a notice that cannot be decided."""

    ntc_id: str
    klass: str
    reason: str
    margin_db: float | None
    case: Case | None = None
    stage_rank: int = 0
    stage: str = ""
    band_use: str = ""
    unknown_field: str = ""  # "psd" or "gain" when the case cannot be computed
    required_db: float | None = None  # value of that field at which margin reaches 0
    filing_action: str = ""  # notice.act_code: A new, M modified, S suppressed
    deadline: date | None = None  # the notice's Resolution 35 deadline, from grp_res35
    deadline_passed: bool = False  # that deadline is already behind the run


@dataclass
class GateResult:
    cases: list[Case]
    undecided: dict[str, str]  # ntc_id -> reason (cannot_decide)
    dropped: dict[str, tuple[str, str]]  # ntc_id -> (stage, reason)
    queue: list[QueueItem] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    drops: dict[str, int] = field(default_factory=dict)
    reference_stations: int = 0
    places: list[Place] = field(default_factory=list)
    bands: list[Band] = field(default_factory=list)
    geo_visible: int = 0
    ngso_visible: int = 0
    mode: str = "slice"
    run_at: str = ""
    input_sha256: str = ""
    rules_version: str = ""
    freq_rows: int = 0
    elapsed_s: float = 0.0
    required: dict[str, tuple[str, float]] = field(default_factory=dict)

    def case_by_id(self) -> dict[str, Case]:
        return {case.ntc_id: case for case in self.cases}

    def reason_counts(self, stage: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for dropped_stage, reason in self.dropped.values():
            if dropped_stage == stage:
                counts[reason] = counts.get(reason, 0) + 1
        return counts


def notice_deadlines(ific: IficData, today: date) -> dict[str, tuple[date, bool]]:
    """Per notice, the Resolution 35 deadline that matters: the earliest one still upcoming among
    the groups of the notice, else the latest one that has passed. The deadline lives on a group
    (`grp_res35.grp_id`), a notice has many; the earliest upcoming is the one to act on.
    A notice whose groups carry no deadline at all is absent."""
    by_notice: dict[str, list[date]] = {}
    for freq in ific.freqs:
        deadline = ific.res35.get(freq.grp_id)
        if deadline is not None:
            by_notice.setdefault(freq.ntc_id, []).append(deadline)
    chosen: dict[str, tuple[date, bool]] = {}
    for ntc_id, dates in by_notice.items():
        upcoming = [value for value in dates if value >= today]
        chosen[ntc_id] = (min(upcoming), False) if upcoming else (max(dates), True)
    return chosen


def queue_key(item: QueueItem) -> tuple:
    """Order inside a class: stage rank, then the earliest upcoming Resolution 35 deadline, then
    margin descending, then the notice id. A passed deadline comes after every upcoming one
    (most recent first), a notice with no deadline last."""
    if item.deadline is None:
        deadline_rank, ordinal = 2, 0
    elif item.deadline_passed:
        deadline_rank, ordinal = 1, -item.deadline.toordinal()
    else:
        deadline_rank, ordinal = 0, item.deadline.toordinal()
    return (item.stage_rank, deadline_rank, ordinal, -(item.margin_db or 0.0), item.ntc_id)


def run(
    ific: IficData,
    stations: list[Station],
    places: list[Place],
    bands: list[Band],
    limits: list[pfd.LimitRow],
    m4_rows: list[dict],
    mode: str = "slice",
    today: date | None = None,
) -> GateResult:
    today = today or date.today()
    found, g1_dropped, adjacent = gate1(ific, bands)
    visible, g2_dropped = gate2(ific, found, places)
    deadlines = notice_deadlines(ific, today)
    cases, undecided, required = gate3(
        ific, visible, stations, places, limits, m4_rows, adjacent, deadlines
    )
    cases.sort(key=lambda case: -case.margin_db)
    dropped = {**g1_dropped, **g2_dropped}
    queue = gate4(cases, undecided, ific.notices, required, deadlines)

    counts = {
        "notices": len(ific.notices),
        "g1": len(found),
        "g2": len(visible),
        "g3": len(cases),
        "cannot_decide": len(undecided),
    }
    for klass in ("exceeds", "near", "not_space", "clear"):
        counts[klass] = sum(1 for case in cases if case.klass == klass)

    result = GateResult(
        cases=cases,
        undecided=undecided,
        required=required,
        dropped=dropped,
        queue=queue,
        counts=counts,
        reference_stations=len(stations),
        places=list(places),
        bands=bands,
        geo_visible=sum(1 for ntc_id in visible if ntc_id in ific.geo),
        ngso_visible=sum(1 for ntc_id in visible if ntc_id not in ific.geo),
        mode=mode,
        input_sha256=ific.input_sha256,
    )
    result.drops = {**result.reason_counts("G1"), **result.reason_counts("G2")}
    return result


def gate1(ific: IficData, bands: list[Band]) -> tuple[dict[str, list[Freq]], dict, set[str]]:
    """Do the notice's space-to-Earth rows overlap a protected band?

    With `GUARD_MHZ > 0` a row that only comes within that distance of a band also passes, and
    the notice is returned in `adjacent` so its case can be capped at class `near`.
    """
    guard = config.GUARD_MHZ
    wanted = [(band.lo_mhz, band.hi_mhz) for band in bands]
    found: dict[str, list[Freq]] = {}
    strictly_matched: set[str] = set()
    for freq in ific.freqs:
        if freq.emi_rcp != "E":
            continue
        overlap = any(freq.freq_min_mhz <= hi and freq.freq_max_mhz >= lo for lo, hi in wanted)
        near = guard > 0 and any(
            freq.freq_min_mhz <= hi + guard and freq.freq_max_mhz >= lo - guard for lo, hi in wanted
        )
        if not overlap and not near:
            continue
        found.setdefault(freq.ntc_id, []).append(freq)
        if overlap:
            strictly_matched.add(freq.ntc_id)

    earth_notices = {n for n in found if ific.notices[n].ntc_type == "S"}
    for ntc_id in earth_notices:
        # An earth station notice sending "E" is the station transmitting, not a downlink.
        del found[ntc_id]

    adjacent = {ntc_id for ntc_id in found if ntc_id not in strictly_matched}
    dropped: dict[str, tuple[str, str]] = {}
    for ntc_id in ific.notices:
        if ntc_id in found:
            continue
        reason = "earth_station_notice" if ntc_id in earth_notices else "no_band_overlap"
        dropped[ntc_id] = ("G1", reason)
    return found, dropped, adjacent


def gate2(
    ific: IficData, found: dict[str, list[Freq]], places: list[Place]
) -> tuple[dict[str, list[Freq]], dict[str, tuple[str, str]]]:
    """Is the satellite visible from Finland at all?"""
    visible: dict[str, list[Freq]] = {}
    dropped: dict[str, tuple[str, str]] = {}
    lat_min = min(abs(place.lat) for place in places)
    for ntc_id, freqs in found.items():
        geo = ific.geo.get(ntc_id)
        if geo is not None and geo.long_nom is not None:
            top = max(pfd.look(place.lat, place.lon, geo.long_nom)[0] for place in places)
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
    places: list[Place],
    limits: list[pfd.LimitRow],
    m4_rows: list[dict],
    adjacent: set[str] | None = None,
    deadlines: dict[str, tuple[date, bool]] | None = None,
) -> tuple[list[Case], dict[str, str], dict[str, tuple[str, float]]]:
    """Worst-case PFD over Finnish territory against the Table 21-4 limit, per notice.

    The third value is the sensitivity of a notice that cannot be computed: the value of the one
    missing field at which its margin would reach 0. `margin = psd + gain - fspl - limit`, so with
    the unknown set to 0 the required value is `-margin`, and no search over a grid is needed.
    """
    adjacent = adjacent or set()
    deadlines = deadlines or {}
    cases: list[Case] = []
    undecided: dict[str, str] = {}
    required: dict[str, tuple[str, float]] = {}
    for ntc_id, freqs in visible.items():
        worst, missing = _worst_for_notice(
            ific,
            ntc_id,
            freqs,
            stations,
            places,
            limits,
            m4_rows,
            ntc_id in adjacent,
            deadline=deadlines.get(ntc_id),
        )
        # shortcut: one second pass with the missing scalar at 0. Both missing is labelled by the
        # first one the loop met, which is enough for the one question a card asks.
        if worst is None and missing in ("no_power", "no_gain"):
            filled, _ = _worst_for_notice(
                ific,
                ntc_id,
                freqs,
                stations,
                places,
                limits,
                m4_rows,
                ntc_id in adjacent,
                fill_unknown=True,
            )
            if filled is not None:
                field_name = {"no_power": "psd", "no_gain": "gain"}.get(missing, missing)
                required[ntc_id] = (field_name, round(-filled.margin_db, 2))
        if worst is None:
            undecided[ntc_id] = missing or "no_territory"
        else:
            cases.append(worst)
    return cases, undecided, required


def _worst_for_notice(
    ific: IficData,
    ntc_id: str,
    freqs: list[Freq],
    stations: list[Station],
    places: list[Place],
    limits: list[pfd.LimitRow],
    m4_rows: list[dict],
    adjacent: bool = False,
    fill_unknown: bool = False,
    deadline: tuple[date, bool] | None = None,
) -> tuple[Case | None, str | None]:
    geo = ific.geo.get(ntc_id)
    sat_lon = geo.long_nom if geo is not None else None
    orbits = ific.orbits.get(ntc_id)
    perigee = None
    counts = (0, 0)  # nbr_sat_nh, nbr_sat_sh
    if sat_lon is not None:
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
            if not fill_unknown:
                missing = "no_power"
                continue
            psd = 0.0
        gain = _beam_gain(ific, freq)
        if gain is None:
            if not fill_unknown:
                missing = "no_gain"
                continue
            gain = 0.0
        offset = 0.0
        if limit.offset == "Y":
            offset = pfd.y_fn(max(counts))
        elif limit.offset == "X":
            x_value = pfd.x_fn(sum(counts))
            if x_value is None:
                missing = "x_needs_nv"
                continue
            offset = x_value
        band = allocation.m4_lookup(m4_rows, freq.freq_min_mhz, freq.freq_max_mhz)
        # The register's rows on this band: context only, never the set the level is taken at.
        reference = [
            station
            for station in stations
            if not (station.hi_mhz < freq.freq_min_mhz or station.lo_mhz > freq.freq_max_mhz)
        ]
        if sat_lon is not None:
            # Every edge point of the territory. The worst case over the area is on the edge.
            points = [
                (place.lat, place.lon, place.label, *pfd.look(place.lat, place.lon, sat_lon))
                for place in places
            ]
            victim = _worst_reference(reference, psd, gain, limit, offset, sat_lon)
        else:
            # shortcut: a non-GSO pass sweeps every latitude, so position does not change the
            # geometry; the pass is sampled from 0 to 90 deg in 0.1 deg steps. Upgrade if a real
            # orbit ephemeris ever arrives.
            points = [(None, None, "", e / 10, pfd.slant(perigee, e / 10)) for e in range(901)]
            victim = reference[0] if reference else None
        for lat, lon, label, elevation, distance in points:
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
                victim=victim,
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
                klass=classify(margin, adjacent, band["space_to_earth"]),
                band_space=band["space_to_earth"],
                band_use=band["services_in_finland"],
                adjacent=adjacent,
                lat=lat,
                lon=lon,
                place=label,
                deadline=deadline[0] if deadline else None,
                deadline_passed=deadline[1] if deadline else False,
            )
    return worst, missing


def _worst_reference(
    reference: list[Station],
    psd: float,
    gain: float,
    limit: pfd.LimitRow,
    offset: float,
    sat_lon: float,
) -> Station | None:
    """The register row with the highest margin on this band, for the card's reference line."""
    worst: Station | None = None
    worst_margin: float | None = None
    for station in reference:
        elevation, distance = pfd.look(station.lat, station.lon, sat_lon)
        if elevation <= 0:
            continue
        margin = round(psd + gain - pfd.fspl(distance) - pfd.limit_hz(limit, elevation, offset), 2)
        if worst_margin is None or margin > worst_margin:
            worst, worst_margin = station, margin
    return worst


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


def gate4(
    cases: list[Case],
    undecided: dict[str, str],
    notices: dict[str, Notice],
    required: dict[str, tuple[str, float]] | None = None,
    deadlines: dict[str, tuple[date, bool]] | None = None,
) -> list[QueueItem]:
    """Queue every concern: class, then stage, then the earliest upcoming Resolution 35 deadline,
    then margin descending; clear stays out.

    Every case is a concern unless the margin is clear *and* Finland allocates the band to a
    satellite downlink: a satellite transmitting where Finland has no such use is a finding on
    its own, whatever the PFD says. No cap: the challenge brief names no target number.
    """
    stages = {ntc_id: config.regulatory_stage(notice.prov) for ntc_id, notice in notices.items()}
    unknown = config.regulatory_stage("")

    required = required or {}
    deadlines = deadlines or {}

    def item(ntc_id, klass, reason, margin, case=None) -> QueueItem:
        stage = stages.get(ntc_id, unknown)
        field_name, value = required.get(ntc_id, ("", None))
        notice = notices.get(ntc_id)
        deadline, passed = deadlines.get(ntc_id, (None, False))
        return QueueItem(
            ntc_id,
            klass,
            reason,
            margin,
            case,
            stage["rank"],
            stage["provision"],
            case.band_use if case is not None else "",
            unknown_field=field_name,
            required_db=value,
            filing_action=notice.act_code if notice is not None else "",
            deadline=deadline,
            deadline_passed=passed,
        )

    items = [
        item(case.ntc_id, case.klass, case.klass, case.margin_db, case)
        for case in cases
        if case.klass != "clear"
    ]
    items += [item(ntc_id, "cannot_decide", reason, None) for ntc_id, reason in undecided.items()]
    queue: list[QueueItem] = []
    for klass in CLASS_ORDER:
        same = [row for row in items if row.klass == klass]
        queue += sorted(same, key=queue_key)
    return queue

"""Read the ITU Space IFIC tables, the Finnish register and the M4 allocation table.

Nothing here computes gates: this module only normalises units and keeps the rows that
app.gates and app.cards need. Everything missing stays None -- the caller decides whether
that is a reason to drop a case, never this module.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

TABLES = (
    "notice",
    "freq",
    "grp",
    "emiss",
    "s_beam",
    "geo",
    "non_geo",
    "orbit",
    "c_pfd",
    "srv_area",
    "srv_cls",
    "e_stn",
    "e_as_stn",
    "assgn",
    "ant_type",
)
# Without notice and freq there is no analysis at all; the other tables may be absent.
REQUIRED_TABLES = ("notice", "freq")

REGISTER_REQUIRED = (
    "Station number",
    "Class of licence",
    "Latitude",
    "Longitude",
    "RX frequency",
    "TX frequency",
    "Ant gain (dB)",
)


class DataError(ValueError):
    """Raised for unusable input files; carries a message a human can act on."""


def num(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_UNIT_RE = re.compile(r"^(-?[\d.,]+)([a-zA-Zµ]*)$")


def mhz(value) -> float | None:
    """'3 520.500 MHz' -> 3520.5 ; '300k' -> 0.3 ; '0,1G' -> 100.0 ; '' -> None."""
    if value is None:
        return None
    text = str(value).replace("\u00a0", "").replace(" ", "").strip()
    if not text:
        return None
    match = _UNIT_RE.match(text)
    if match is None:
        return None
    try:
        number = float(match.group(1).replace(",", "."))
    except ValueError:
        return None
    unit = match.group(2).lower()
    if unit in ("ghz", "g"):
        number *= 1000
    elif unit in ("khz", "k"):
        number /= 1000
    elif unit in ("hz", "h"):
        number /= 1e6
    return number


_POWER_FACTOR = {"": 1.0, "w": 1.0, "kw": 1e3, "mw": 1e-3}


def watts(value, unit) -> float | None:
    """'145' + 'W' -> 145.0 ; '2' + 'kW' -> 2000.0."""
    number = num(value)
    if number is None:
        return None
    return number * _POWER_FACTOR.get(str(unit or "").strip().lower(), 1.0)


def rows(path: Path, required: tuple[str, ...] = ()) -> list[dict]:
    """Read a CSV, or raise DataError naming the file and the missing column."""
    if not path.is_file():
        raise DataError(f"missing input file: {path}")
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames
        if not header:
            raise DataError(f"{path.name}: empty file, no header row")
        for column in required:
            if column not in header:
                raise DataError(f"{path.name}: missing column {column!r}")
        data = list(reader)
    if not data:
        raise DataError(f"{path.name}: header only, no data rows")
    return data


@dataclass(frozen=True)
class Station:
    """One Finnish register row that has a frequency and coordinates."""

    id: str
    licence: str
    lat: float
    lon: float
    rx_mhz: float | None
    tx_mhz: float | None
    bw_mhz: float
    gain_db: float | None
    power_w: float | None
    direction_deg: float | None
    ant_asl_m: float | None
    ground_m: float | None

    @property
    def centre_mhz(self) -> float:
        return self.rx_mhz if self.rx_mhz is not None else (self.tx_mhz or 0.0)

    @property
    def lo_mhz(self) -> float:
        return self.centre_mhz - self.bw_mhz / 2

    @property
    def hi_mhz(self) -> float:
        return self.centre_mhz + self.bw_mhz / 2


@dataclass(frozen=True)
class Freq:
    ntc_id: str
    beam_name: str
    grp_id: str
    emi_rcp: str
    freq_min_mhz: float
    freq_max_mhz: float


@dataclass(frozen=True)
class Beam:
    ntc_id: str
    beam_name: str
    gain_db: float | None
    freq_min_mhz: float | None
    freq_max_mhz: float | None
    geometry: dict  # bore_long, bore_lat, maj_axis, min_axis: empty in IFIC 3074


@dataclass(frozen=True)
class Notice:
    ntc_id: str
    adm: str
    ntc_type: str
    act_code: str
    ntwk_org: str
    adm_ref_id: str
    tgt_ntc_id: str


@dataclass(frozen=True)
class Geo:
    ntc_id: str
    sat_name: str
    long_nom: float | None


@dataclass(frozen=True)
class NonGeo:
    ntc_id: str
    sat_name: str
    nbr_sat_nh: int
    nbr_sat_sh: int


@dataclass(frozen=True)
class Orbit:
    ntc_id: str
    apog_km: float | None
    perig_km: float | None
    inclin_ang: float | None


@dataclass(frozen=True)
class IficData:
    notices: dict[str, Notice]
    freqs: list[Freq]
    beams: dict[tuple[str, str], list[Beam]]
    emiss: dict[str, float]  # grp_id -> max pwr_ds_max, dBW/Hz
    geo: dict[str, Geo]
    nongeo: dict[str, NonGeo]
    orbits: dict[str, list[Orbit]]
    counts: dict[str, int]
    file: str
    input_sha256: str

    def sat_name(self, ntc_id: str) -> str:
        geo = self.geo.get(ntc_id)
        if geo is not None:
            return geo.sat_name
        nongeo = self.nongeo.get(ntc_id)
        return nongeo.sat_name if nongeo is not None else ""

    def beam(self, ntc_id: str, beam_name: str) -> Beam | None:
        beams = self.beams.get((ntc_id, beam_name))
        return beams[0] if beams else None

    def same_network(self, ntc_id: str) -> list[str]:
        """Other notices of the same network: same satellite and administration, or a
        notified target. The card shows them; each notice is still decided on its own."""
        notice = self.notices.get(ntc_id)
        if notice is None:
            return []
        name = self.sat_name(ntc_id)
        chain = {notice.tgt_ntc_id} if notice.tgt_ntc_id else set()
        out = []
        for other_id, other in self.notices.items():
            if other_id == ntc_id:
                continue
            same_name = bool(name) and self.sat_name(other_id) == name and other.adm == notice.adm
            if same_name or other_id in chain or other.tgt_ntc_id == ntc_id:
                out.append(other_id)
        return sorted(out)


def load_register(path: Path) -> tuple[list[Station], dict[str, int]]:
    """Register rows as Stations, plus counters for the rows that were skipped."""
    data = rows(path, REGISTER_REQUIRED)
    stations: list[Station] = []
    no_freq = no_position = 0
    for row in data:
        rx_mhz, tx_mhz = mhz(row["RX frequency"]), mhz(row["TX frequency"])
        if rx_mhz is None and tx_mhz is None:
            no_freq += 1
            continue
        lat, lon = num(row["Latitude"]), num(row["Longitude"])
        if lat is None or lon is None:
            no_position += 1
            continue
        # The register's Channel bandwidth is the raster the station sits in; Transmission
        # bandwidth is what it actually emits. Use the channel, fall back to the emission.
        bandwidth = (
            mhz(row.get("Channel bandwidth")) or mhz(row.get("Transmission bandwidth")) or 0.0
        )
        stations.append(
            Station(
                id=row["Station number"].strip(),
                licence=row["Class of licence"].strip(),
                lat=lat,
                lon=lon,
                rx_mhz=rx_mhz,
                tx_mhz=tx_mhz,
                bw_mhz=bandwidth,
                gain_db=num(row["Ant gain (dB)"]),
                power_w=watts(row.get("Radioation power"), row.get("Radiation power unit")),
                direction_deg=num(row.get("Radiation direction (°)")),
                ant_asl_m=num(row.get("Ant height ASL (m)")),
                ground_m=num(row.get("Ground height (m)")),
            )
        )
    counts = {"rows": len(data), "stations": len(stations), "skipped_no_freq": no_freq}
    if no_position:
        counts["skipped_no_position"] = no_position
    return stations, counts


def load_m4(path: Path) -> list[dict]:
    """Traficom open data: the table of frequency allocations (Regulation M4 annex)."""
    if not path.is_file():
        raise DataError(f"missing input file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise DataError(f"{path.name}: not valid JSON ({error})") from error
    value = payload.get("value") if isinstance(payload, dict) else payload
    if not isinstance(value, list) or not value:
        raise DataError(f"{path.name}: no 'value' array with allocation rows")
    return value


def load_ific(ific_dir: Path) -> IficData:
    """Read the 15 IFIC tables from <ific_dir>/csv; only notice and freq are mandatory."""
    csv_dir = ific_dir / "csv"
    if not csv_dir.is_dir():
        raise DataError(f"missing IFIC directory: {csv_dir}")
    tables = {name: csv_dir / f"{name}.csv" for name in TABLES}
    for name in REQUIRED_TABLES:
        if not tables[name].is_file():
            raise DataError(f"missing input file: {tables[name]}")

    notices = {
        row["ntc_id"]: Notice(
            ntc_id=row["ntc_id"],
            adm=row["adm"].strip(),
            ntc_type=row["ntc_type"].strip(),
            act_code=row["act_code"].strip(),
            ntwk_org=row.get("ntwk_org", "").strip(),
            adm_ref_id=row.get("adm_ref_id", "").strip(),
            tgt_ntc_id=row.get("tgt_ntc_id", "").strip(),
        )
        for row in rows(tables["notice"], ("ntc_id", "adm", "ntc_type", "act_code"))
    }

    freqs = []
    for row in rows(tables["freq"], ("ntc_id", "emi_rcp", "freq_min", "freq_max")):
        lo, hi = mhz(row["freq_min"]), mhz(row["freq_max"])
        if lo is None or hi is None:
            continue  # a frequency row without a frequency cannot be used
        freqs.append(
            Freq(
                ntc_id=row["ntc_id"],
                beam_name=row.get("beam_name", "").strip(),
                grp_id=row.get("grp_id", "").strip(),
                emi_rcp=row["emi_rcp"].strip(),
                freq_min_mhz=min(lo, hi),
                freq_max_mhz=max(lo, hi),
            )
        )

    beams: dict[tuple[str, str], list[Beam]] = {}
    if tables["s_beam"].is_file():
        for row in rows(tables["s_beam"], ("ntc_id", "beam_name")):
            beam = Beam(
                ntc_id=row["ntc_id"],
                beam_name=row["beam_name"].strip(),
                gain_db=num(row["gain"]),
                freq_min_mhz=num(row["freq_min"]),
                freq_max_mhz=num(row["freq_max"]),
                geometry={
                    key: num(row.get(key))
                    for key in ("bore_long", "bore_lat", "maj_axis", "min_axis")
                },
            )
            beams.setdefault((beam.ntc_id, beam.beam_name), []).append(beam)

    emiss: dict[str, float] = {}
    if tables["emiss"].is_file():
        for row in rows(tables["emiss"], ("grp_id",)):
            value = num(row.get("pwr_ds_max"))
            if value is not None:
                grp_id = row["grp_id"]
                emiss[grp_id] = max(emiss.get(grp_id, float("-inf")), value)

    geo = {}
    if tables["geo"].is_file():
        for row in rows(tables["geo"], ("ntc_id",)):
            geo[row["ntc_id"]] = Geo(
                ntc_id=row["ntc_id"],
                sat_name=row.get("sat_name", "").strip(),
                long_nom=num(row.get("long_nom")),
            )

    nongeo = {}
    if tables["non_geo"].is_file():
        for row in rows(tables["non_geo"], ("ntc_id",)):
            nongeo[row["ntc_id"]] = NonGeo(
                ntc_id=row["ntc_id"],
                sat_name=row.get("sat_name", "").strip(),
                nbr_sat_nh=int(num(row.get("nbr_sat_nh")) or 0),
                nbr_sat_sh=int(num(row.get("nbr_sat_sh")) or 0),
            )

    orbits: dict[str, list[Orbit]] = {}
    if tables["orbit"].is_file():
        for row in rows(tables["orbit"], ("ntc_id",)):
            orbits.setdefault(row["ntc_id"], []).append(
                Orbit(
                    ntc_id=row["ntc_id"],
                    apog_km=num(row.get("apog_km")),
                    perig_km=num(row.get("perig_km")),
                    inclin_ang=num(row.get("inclin_ang")),
                )
            )

    counts = {name: 0 for name in TABLES}
    counts["notice"] = len(notices)
    counts["freq"] = len(freqs)
    counts["s_beam"] = sum(len(v) for v in beams.values())
    counts["orbit"] = sum(len(v) for v in orbits.values())
    for name in (
        "grp",
        "emiss",
        "geo",
        "non_geo",
        "c_pfd",
        "srv_area",
        "srv_cls",
        "e_stn",
        "e_as_stn",
        "assgn",
        "ant_type",
    ):
        if counts[name] == 0 and tables[name].is_file():
            counts[name] = line_count(tables[name])
    mdb = sorted(ific_dir.glob("*.mdb"))
    return IficData(
        notices=notices,
        freqs=freqs,
        beams=beams,
        emiss=emiss,
        geo=geo,
        nongeo=nongeo,
        orbits=orbits,
        counts=counts,
        file=mdb[0].name if mdb else f"{ific_dir.name}.zip",
        input_sha256=input_digest([tables[name] for name in TABLES] + [ific_dir]),
    )


def line_count(path: Path) -> int:
    """Data rows of a table that is only counted (never analysed)."""
    with path.open(encoding="utf-8", errors="replace") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_digest(paths: list[Path]) -> str:
    """One hash over every input file (name + bytes), so a rerun on other data is visible."""
    digest = hashlib.sha256()
    for path in sorted(p for p in paths if p.is_file()):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()

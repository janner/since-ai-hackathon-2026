"""Read the ITU Space IFIC tables, the Finnish register and the M4 allocation table.

Nothing here computes gates: this module only normalises units and keeps the rows that
app.gates and app.cards need. Everything missing stays None -- the caller decides whether
that is a reason to drop a case, never this module.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime
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
    "ntc_lnk",
    "grp_res35",
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


def deadline(value) -> date | None:
    """'12/19/26 00:00:00' -> date(2026, 12, 19). `mdb-export` renders a date column in the
    database's own format; anything that is not that shape stays None rather than guessing."""
    try:
        return datetime.strptime(str(value or "").strip(), "%m/%d/%y %H:%M:%S").date()
    except ValueError:
        return None


def iter_rows(path: Path, required: tuple[str, ...] = ()):
    """Stream a CSV row by row; the same errors as `rows()`, without holding the file."""
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
        seen = 0
        for row in reader:
            seen += 1
            yield row
        if not seen:
            raise DataError(f"{path.name}: header only, no data rows")


def rows(path: Path, required: tuple[str, ...] = ()) -> list[dict]:
    """Read a CSV, or raise DataError naming the file and the missing column."""
    return list(iter_rows(path, required))


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
    directivity: str = ""

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
    prov: str
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
class Link:
    """One ntc_lnk row: the filing follows `ntc_id`, a notice of the nature `reason`."""

    ntc_id: str
    reason: str


@dataclass(frozen=True)
class IficData:
    notices: dict[str, Notice]
    freqs: list[Freq]
    beams: dict[tuple[str, str], list[Beam]]
    emiss: dict[str, float]  # grp_id -> max pwr_ds_max, dBW/Hz
    geo: dict[str, Geo]
    nongeo: dict[str, NonGeo]
    orbits: dict[str, list[Orbit]]
    links: dict[str, list[Link]]  # ntc_id -> the notices it follows (ntc_lnk)
    counts: dict[str, int]
    file: str
    input_sha256: str
    res35: dict[str, date] = field(default_factory=dict)  # grp_id -> Resolution 35 deadline

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


def load_register(
    path: Path, bands: tuple[tuple[float, float], ...] | None = None
) -> tuple[list[Station], dict[str, int]]:
    """Register rows as Stations, plus counters for the rows that were skipped.

    `bands` (lo, hi MHz) keeps only the stations whose channel touches one of them. The file
    is streamed, so a register far larger than memory still loads.
    """
    stations: list[Station] = []
    no_freq = no_position = total = 0
    for row in iter_rows(path, REGISTER_REQUIRED):
        total += 1
        rx_mhz, tx_mhz = mhz(row["RX frequency"]), mhz(row["TX frequency"])
        if rx_mhz is None and tx_mhz is None:
            no_freq += 1
            continue
        lat, lon = num(row["Latitude"]), num(row["Longitude"])
        if lat is None or lon is None:
            no_position += 1
            continue
        # Traficom: when Channel bandwidth and Transmission bandwidth disagree, the smaller
        # one is what the register means (the larger is a data-entry artefact). A missing one
        # falls back to the other.
        channel, transmission = (
            mhz(row.get("Channel bandwidth")),
            mhz(row.get("Transmission bandwidth")),
        )
        if channel is not None and transmission is not None:
            bandwidth = min(channel, transmission)
        else:
            bandwidth = channel or transmission or 0.0
        centre = rx_mhz if rx_mhz is not None else (tx_mhz or 0.0)
        if bands is not None and not any(
            lo <= centre + bandwidth / 2 and hi >= centre - bandwidth / 2 for lo, hi in bands
        ):
            continue
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
                directivity=row.get("Directivity", "").strip(),
            )
        )
    counts = {"rows": total, "stations": len(stations), "skipped_no_freq": no_freq}
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


def _export(mdb: Path, table: str) -> list[dict]:
    """One IFIC table straight from the Access database: `mdb-export <mdb> <table>`."""
    if shutil.which("mdb-export") is None:
        raise DataError("mdb-export not found: install mdbtools (apt install mdbtools)")
    result = subprocess.run(
        ["mdb-export", str(mdb), table], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise DataError(f"{mdb.name}: mdb-export {table} failed: {result.stderr.strip()}")
    return list(csv.DictReader(io.StringIO(result.stdout)))


def load_ific(mdb_path: Path) -> IficData:
    """Read the 17 IFIC tables straight from the BR IFIC Access database.

    `mdb-export <mdb> <table>` per table: no shell, no intermediate CSV directory. Only
    `notice` and `freq` are mandatory; a table the export cannot read is treated as absent.
    """
    mdb = Path(mdb_path)
    if not mdb.is_file():
        raise DataError(f"missing input file: {mdb}")

    tables: dict[str, list[dict]] = {}
    for name in TABLES:
        try:
            tables[name] = _export(mdb, name)
        except DataError:
            if name in REQUIRED_TABLES:
                raise
            tables[name] = []

    def table(name: str, columns: tuple[str, ...]) -> list[dict]:
        """The rows of one table, with its required columns checked; empty if absent."""
        data = tables[name]
        if not data:
            if name in REQUIRED_TABLES:
                raise DataError(f"{mdb.name}: table {name!r} is empty")
            return []
        for column in columns:
            if column not in data[0]:
                raise DataError(f"{mdb.name}: table {name!r} missing column {column!r}")
        return data

    notices = {
        row["ntc_id"]: Notice(
            ntc_id=row["ntc_id"],
            adm=row["adm"].strip(),
            ntc_type=row["ntc_type"].strip(),
            act_code=row["act_code"].strip(),
            prov=row.get("prov", "").strip(),
            ntwk_org=row.get("ntwk_org", "").strip(),
            adm_ref_id=row.get("adm_ref_id", "").strip(),
            tgt_ntc_id=row.get("tgt_ntc_id", "").strip(),
        )
        for row in table("notice", ("ntc_id", "adm", "ntc_type", "act_code"))
    }

    freqs = []
    for row in table("freq", ("ntc_id", "emi_rcp", "freq_min", "freq_max")):
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
    for row in table("s_beam", ("ntc_id", "beam_name")):
        beam = Beam(
            ntc_id=row["ntc_id"],
            beam_name=row["beam_name"].strip(),
            gain_db=num(row["gain"]),
            freq_min_mhz=num(row["freq_min"]),
            freq_max_mhz=num(row["freq_max"]),
            geometry={
                key: num(row.get(key)) for key in ("bore_long", "bore_lat", "maj_axis", "min_axis")
            },
        )
        beams.setdefault((beam.ntc_id, beam.beam_name), []).append(beam)

    emiss: dict[str, float] = {}
    for row in table("emiss", ("grp_id",)):
        value = num(row.get("pwr_ds_max"))
        if value is not None:
            grp_id = row["grp_id"]
            emiss[grp_id] = max(emiss.get(grp_id, float("-inf")), value)

    geo = {}
    for row in table("geo", ("ntc_id",)):
        geo[row["ntc_id"]] = Geo(
            ntc_id=row["ntc_id"],
            sat_name=row.get("sat_name", "").strip(),
            long_nom=num(row.get("long_nom")),
        )

    nongeo = {}
    for row in table("non_geo", ("ntc_id",)):
        nongeo[row["ntc_id"]] = NonGeo(
            ntc_id=row["ntc_id"],
            sat_name=row.get("sat_name", "").strip(),
            nbr_sat_nh=int(num(row.get("nbr_sat_nh")) or 0),
            nbr_sat_sh=int(num(row.get("nbr_sat_sh")) or 0),
        )

    orbits: dict[str, list[Orbit]] = {}
    for row in table("orbit", ("ntc_id",)):
        orbits.setdefault(row["ntc_id"], []).append(
            Orbit(
                ntc_id=row["ntc_id"],
                apog_km=num(row.get("apog_km")),
                perig_km=num(row.get("perig_km")),
                inclin_ang=num(row.get("inclin_ang")),
            )
        )

    # ntc_lnk: the notice a filing follows. A row without a target is not a link.
    links: dict[str, list[Link]] = {}
    for row in table("ntc_lnk", ("ntc_id", "lnk_ntc_id", "lnkntf_rsn")):
        followed = row["lnk_ntc_id"].strip()
        if followed:
            links.setdefault(row["ntc_id"], []).append(
                Link(ntc_id=followed, reason=row["lnkntf_rsn"].strip())
            )

    # grp_res35: the Resolution 35 deadline of a group (an empty or unreadable date is dropped,
    # the group then simply has no deadline).
    res35: dict[str, date] = {}
    for row in table("grp_res35", ("grp_id", "d_ms_next_deadline")):
        value = deadline(row["d_ms_next_deadline"])
        if value is not None:
            res35[row["grp_id"].strip()] = value

    counts = {name: len(data) for name, data in tables.items()}
    counts["notice"] = len(notices)
    counts["freq"] = len(freqs)
    counts["s_beam"] = sum(len(v) for v in beams.values())
    counts["orbit"] = sum(len(v) for v in orbits.values())
    return IficData(
        notices=notices,
        freqs=freqs,
        beams=beams,
        emiss=emiss,
        geo=geo,
        nongeo=nongeo,
        orbits=orbits,
        links=links,
        counts=counts,
        file=mdb.name,
        input_sha256=sha256(mdb),
        res35=res35,
    )


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

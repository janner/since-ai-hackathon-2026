"""Terrestriaalinen sivutehtävä: BR IFIC -MDB Suomen rekisteriä vasten.

Sama ohjelma ja sama tulostekontrakti, eri laskentapolku. Jaettu ydin on
`app.ingest`-moduulin provenienssi (`sha256`, `input_digest`) ja
`app.config.RULES_VERSION`; tuloste kantaa samat kentät kuin avaruuspuolen kortti
(`source`, `audit`, `missing`), mutta laskenta on ITU-R P.1546-6 eikä PFD-portit.
Ajo tapahtuu samalla komennolla (`app.pipeline --terrestrial`); ilman lippua
avaruusajo on ennallaan. Moduuli lukee omat syötteensä (BR IFIC -MDB
`mdb-export`illa, kuten `scripts/fetch_data.py`) ja kirjoittaa omat kolme
tulostetiedostonsa (päätös D7).

Ilmoituksen tila tulee `fxm_terra.intent`-kentästä (ADD/MODIFY/SUPPRESS/RECORDED):
IFIC ei ole kumulatiivinen kanta, joten kahden numeron avainvertailu ei kerro
muutoksista. 3075 on trendien vertailupohja.

Malli: ITU-R P.1546-6 maapolku, 10 % ajasta (sama aikaprosentti kuin T/R 25-08
A1.2.3 -kynnyksellä), 50 % paikoista, ei maastoa, vastaanottoantenni 10 m. Taulukko
`rules/p1546_land.csv` on generoitu ITU:n referenssitoteutuksella (eeveetza/Py1546,
commit e235629) skriptillä `scripts/gen_p1546_table.py`:

    bt_loss(f, 10, h1, 10, 10, "Rural", [d], ["Land"], 0, 50, 0, 1, h1)[0]

taajuuksilla 100/600/2000 MHz, korkeuksilla 10/20/37.5/75/150/300/600/1200 m ja
P.1546:n nimellisetäisyyksillä 1–1000 km. Taulukon arvot ovat 1 kW ERP
-referenssille, joten teho lisätään 10*log10(p). Interpolointi P.1546-6 Annex 5:n
mukaan logaritmisena: etäisyys log d (eq. 15), korkeus log h1 (eq. 8) ja taajuus
log f (eq. 14; alle 100 ja yli 2000 MHz ekstrapoloidaan kahdesta lähimmästä käyrästä).
Korkeus alle 10 m kiinnitetään 10 m:iin (yliarvio, Annex 5 §4.2 eq. 9 jätetty
toteuttamatta) ja korkeus yli 1200 m sekä etäisyys alle 1 tai yli 1000 km taulukon
reunaan; nämä merkitään `extrapolated`-lipulla, kun maksimipiste osuu niihin.

Traficomin Q&A 7.11.2026: kenttävoimakkuus lasketaan **rajaviivan pisteissä**, ei
neljässä kaupungissa, ja lisäksi merkitään ne rekisterin suomalaiset asemat, joiden
kenttävoimakkuus ylittää koordinointikynnyksen. Rajaviiva on `rules/finland_border.csv`:
maanrajat Ruotsin (SE), Norjan (NO) ja Venäjän (RU) kanssa sekä alueveden ulkoraja
(TS, 12 mp:n viiva; Traficom 7.11.2026). Rantaviiva ei ole rajaviivaa. Pisteet
jaetaan `section`-sarakkeella peräkkäisiin murtoviivoihin, jotta tuloksesta näkyy,
**missä osassa** kenttävoimakkuus on suurin (Traficom 7.11.).
Kynnys on CEPT/ECC T/R 25-08 A1.2.3
(`rules/tr2508_thresholds.csv`); Traficomin 7.11.2026 mukaan sama kriteeri jatkuu
yli 470 MHz:n, missä on 85 % aineiston maaliikenteen riveistä.
"""

import argparse
import csv
import json
import math
from collections import Counter
from datetime import UTC, datetime
from functools import cache, lru_cache
from pathlib import Path

from app.config import RULES_VERSION
from app.ingest import _export, input_digest, sha256

RULES = Path(__file__).resolve().parent.parent / "rules" / "p1546_land.csv"
BORDER = Path(__file__).resolve().parent.parent / "rules" / "finland_border.csv"
TR2508 = Path(__file__).resolve().parent.parent / "rules" / "tr2508_thresholds.csv"

# BR IFIC 3076 -skeeman taulut, joista notice rakennetaan.
TABLES = ("fxm_terra", "fxm_geo", "fxm_ant", "fxm_coord")
# Tulosteen `source.keys`: mistä taulujen avaimista luku tuli (SCOPE 7, sama kontrakti
# kuin avaruuskortin `ntc_id` / `grp_id` / `beam_name`).
KEYS = ("terrakey", "adm_ref_id")
# intent -> muutoksen nimi. RECORDED on kanta, ei muutos.
INTENT_CHANGE = {"ADD": "new", "MODIFY": "modified", "SUPPRESS": "withdrawn"}

MAX_DIST_KM = 1000.0
RX_HEIGHT_M = 10.0
# Kenttävoimakkuus lasketaan rajaviivan pisteissä: murtoviiva näytellään tällä
# välein, jotta myös pitkät suorat rajaosat tulevat katetuiksi (Traficom 7.11.).
BORDER_STEP_KM = 10.0
KM_PER_DEG = 111.32
TR2508_REF_BW_KHZ = 25.0
# BR IFIC -asemaluokat: FB = tukiasema, ML = maaliikenne, FL = maaliikenne (kiinteä).
LAND_MOBILE_CLASSES = frozenset({"FB", "ML", "FL"})
# Naapurihallinnot ITU-koodein (S = Ruotsi). Trendit ja poikkeamat rajataan näihin
# sekä hallintoihin, joiden ilmoitus on < MAX_DIST_KM Suomen rajasta.
NEIGHBOURS = frozenset({"RUS", "S", "NOR", "EST", "LVA", "LTU"})
# ML-asemalla ei ole antennikorkeutta. Oletus = taulukon matalin korkeus 10 m: se on
# korkeampi kuin ajoneuvoantenni, joten arvo on yliarvio eikä kätke ylitystä.
ASSUMED_H1_M = 10.0
# Rajaosat (rules/finland_border.csv `section`): maanrajat Ruotsin, Norjan ja
# Venäjän kanssa sekä aluevesiraja. Traficom 7.11.2026: arviointi tehdään maanrajoja
# ja alueveden ulkorajaa pitkin, ei pelkkää mantereen rantaviivaa. Alueveden
# ulkoraja on 12 mp:n viiva (Marine Regions, Finnish 12 NM).
SECTION_NAMES = {
    "SE": "Ruotsi (Tornionlaakso, maanraja)",
    "NO": "Norja (Käsivarsi, maanraja)",
    "RU": "Venäjä (itäraja, maanraja)",
    "TS": "Aluevesiraja (12 mp:n ulkoraja)",
}
# Traficom 7.11.2026: T/R 25-08 päättyy 470 MHz:iin, ja sen yläpuolella sovelletaan
# samaa kriteeriä kuin 400-470 MHz:n alueella (20 dB(uV/m) + kaistanleveyskorjaus).
# Ilman tätä 85 % 3076:n maaliikenteen riveistä jäisi ilman kynnystä.
CRITERION = (
    "protection framework in three tiers: "
    "ITU Radio Regulations terrestrial notification (Article 11, the notice's own "
    "fxm_terra.prov, e.g. RR11.2 / RR11.9; coordination under Article 9 or a regional "
    "agreement) with each notice's own coordination provision and status from "
    "fxm_coord (coord_prov as recorded, e.g. RR6.7 or GE06 4.2.2.2) -> "
    "CEPT/ECC T/R 25-08 A1.2.3 (coordination threshold at the border line, "
    "25 kHz reference bandwidth, 10 % time, 10 m receiving antenna; Traficom "
    "7.11.2026 applies the 400-470 MHz criterion above 470 MHz) applies here -> "
    "national M4 / Traficomin taajuusjakotaulukko (national M4 value not confirmed)"
)
TIME_PERCENT = 10


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mhz(value):
    """'87.900 MHz' / '300.000 kHz' / '1.5 GHz' -> MHz. None jos ei luettavissa."""
    parts = str(value or "").split()
    if len(parts) != 2 or parts[1].lower() not in {"khz", "mhz", "ghz"}:
        return None
    number = _num(parts[0])
    if number is None:
        return None
    return number * {"khz": 1e-3, "mhz": 1.0, "ghz": 1e3}[parts[1].lower()]


def _khz(value):
    """'300.000 kHz' / '16 kHz' -> kHz. None jos ei luettavissa."""
    parts = str(value or "").split()
    if len(parts) != 2 or parts[1].lower() not in {"hz", "khz", "mhz"}:
        return None
    number = _num(parts[0])
    if number is None:
        return None
    return number * {"hz": 1e-3, "khz": 1.0, "mhz": 1e3}[parts[1].lower()]


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


@lru_cache(maxsize=1)
def border_line():
    """Suomen raja: maanrajat ja alueveden ulkoraja (lat, lon, section).

    `section` = rajaosa: SE (Tornionlaakso, Ruotsin maanraja), NO (Norjan
    maanraja), RU (Venäjän maanraja), TS (alueveden ulkoraja, 12 mp:n viiva).
    Traficom 7.11.2026: arviointi tehdään maanrajoja ja alueveden ulkorajaa
    pitkin. Pisteet jaetaan peräkkäisiin murtoviivoihin `section`-arvon
    vaihtuessa; TS on oma suljettu renkaansa. Rantaviiva ei ole rajaviivaa.
    """
    points = []
    with BORDER.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            points.append((float(row["lat"]), float(row["lon"]), row["section"]))
    if len(points) < 3:
        raise ValueError(f"{BORDER}: rajaviiva tarvitsee vähintään 3 pistettä")
    lines, current = [], []
    for point in points:
        if current and point[2] != current[-1][2]:
            lines.append(tuple(current))
            current = []
        current.append(point)
    if current:
        lines.append(tuple(current))
    return tuple(lines)


@lru_cache(maxsize=1)
def border_samples():
    """Rajaviiva tasavälein (`BORDER_STEP_KM`): kenttävoimakkuuden laskentapisteet.

    Jokainen näyte kantaa sen janan rajaosan, jolla se on, joten maksimi voidaan
    laskea rajaosittain. Murtoviivat ovat avoimia; TS sulkeutuu itsestään, koska
    sen ensimmäinen ja viimeinen piste ovat samat.
    """
    samples = []
    for line in border_line():
        for i in range(len(line) - 1):
            a, b = line[i], line[i + 1]
            steps = max(1, int(haversine_km(a[0], a[1], b[0], b[1]) / BORDER_STEP_KM))
            for j in range(steps):
                w = j / steps
                samples.append((a[0] + (b[0] - a[0]) * w, a[1] + (b[1] - a[1]) * w, a[2]))
    return tuple(samples)


def _point_segment_km(lat, lon, a, b):
    """Etäisyys pisteestä janan ab päälle: paikallinen taso (riittää 1 000 km:lle)."""
    k = math.cos(math.radians(lat))
    ax, ay = (a[1] - lon) * k * KM_PER_DEG, (a[0] - lat) * KM_PER_DEG
    bx, by = (b[1] - lon) * k * KM_PER_DEG, (b[0] - lat) * KM_PER_DEG
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(ax, ay)
    t = max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy)))
    return math.hypot(ax + t * dx, ay + t * dy)


@cache
def distance_to_border_km(lat, lon):
    """Lyhin etäisyys Suomen rajaan: maanrajat ja alueveden ulkoraja (T2)."""
    return min(
        _point_segment_km(lat, lon, line[i], line[i + 1])
        for line in border_line()
        for i in range(len(line) - 1)
    )


@lru_cache(maxsize=1)
def tr2508_rows():
    rows = []
    with TR2508.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append((float(row["f_min_mhz"]), float(row["f_max_mhz"]), float(row["dbuv_m"])))
    if not rows:
        raise ValueError(f"{TR2508}: kynnystaulukko on tyhjä")
    return tuple(rows)


def tr2508_threshold(freq_mhz, bw_khz=TR2508_REF_BW_KHZ):
    """T/R 25-08 A1.2.3 -koordinointikynnys dB(uV/m) 25 kHz vertailukaistalla.

    None vain alle 29,7 MHz:n. Traficomin 7.11.2026 mukaan yli 470 MHz:llä
    sovelletaan samaa kriteeriä kuin 400-470 MHz:n alueella (20 dB(uV/m)).
    Kaistanleveydelle > 25 kHz lisätään A1.2.3:n korjaus 10*log10(bw/25) dB.
    """
    if freq_mhz is None:
        return None
    for f_min, f_max, dbuv in tr2508_rows():
        if f_min <= freq_mhz <= f_max:
            if bw_khz and bw_khz > TR2508_REF_BW_KHZ:
                return dbuv + 10 * math.log10(bw_khz / TR2508_REF_BW_KHZ)
            return dbuv
    return None


@lru_cache(maxsize=1)
def _grid():
    grid = {}
    with RULES.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key = (float(row["f_mhz"]), float(row["h1_m"]), float(row["d_km"]))
            grid[key] = float(row["e_dbuv_m"])
    if not grid:
        raise ValueError(f"{RULES}: P.1546-taulukko on tyhjä")
    return grid


@lru_cache(maxsize=1)
def _axes():
    keys = _grid().keys()
    return (
        tuple(sorted({k[0] for k in keys})),
        tuple(sorted({k[1] for k in keys})),
        tuple(sorted({k[2] for k in keys})),
    )


def _log_bracket(axis, x, extrapolate=False):
    """(ala, ylä, paino) logaritmisella painolla log(x/ala)/log(ylä/ala) (Annex 5).

    Akselin ulkopuolella joko ekstrapoloidaan kahdesta lähimmästä pisteestä
    (`extrapolate`, taajuus Annex 5:n mukaan) tai kiinnitytään reunapisteeseen.
    """
    if x <= axis[0] or x >= axis[-1]:
        lo, hi = (axis[0], axis[1]) if x <= axis[0] else (axis[-2], axis[-1])
        if not extrapolate:
            edge = axis[0] if x <= axis[0] else axis[-1]
            return edge, edge, 0.0
    else:
        lo, hi = next((a, b) for a, b in zip(axis, axis[1:], strict=False) if a <= x <= b)
    return lo, hi, math.log(x / lo) / math.log(hi / lo)


def field_strength_p1546(freq_mhz, dist_km, h_ant_m, p_erp_kw):
    """Kenttävoimakkuus dB(uV/m): P.1546-6 maapolku, 10 % ajasta, 50 % paikoista.

    Logaritminen interpolointi taajuudessa, antennikorkeudessa ja etäisyydessä
    (P.1546-6 Annex 5 eq. 8, 14, 15); 1 kW -arvo rajataan vapaan tilan arvoon
    Efs = 106.9 - 20 log d (Annex 5 eq. 2), jottei taajuusekstrapolointi ylitä sitä.
    Palauttaa None, jos syöte ei ole fysikaalinen (esim. etäisyys 0).
    """
    if None in (freq_mhz, dist_km, h_ant_m, p_erp_kw):
        return None
    if dist_km <= 0 or p_erp_kw <= 0 or h_ant_m <= 0 or freq_mhz <= 0:
        return None
    grid = _grid()
    f_ax, h_ax, d_ax = _axes()
    f_lo, f_hi, wf = _log_bracket(f_ax, float(freq_mhz), extrapolate=True)
    h_lo, h_hi, wh = _log_bracket(h_ax, float(h_ant_m))
    d_lo, d_hi, wd = _log_bracket(d_ax, float(dist_km))
    e = 0.0
    for f, w_f in ((f_lo, 1 - wf), (f_hi, wf)):
        for h, w_h in ((h_lo, 1 - wh), (h_hi, wh)):
            for d, w_d in ((d_lo, 1 - wd), (d_hi, wd)):
                e += w_f * w_h * w_d * grid[(f, h, d)]
    efs = 106.9 - 20 * math.log10(min(max(dist_km, d_ax[0]), d_ax[-1]))
    return min(e, efs) + 10 * math.log10(p_erp_kw)


def extrapolated(freq_mhz, dist_km, h_ant_m):
    """Onko kysely taulukon ulkopuolella (kiinnitys tai Annex 5 -ekstrapolointi).

    Kaikki kolme akselia, molemmin puolin: taajuus alle 100 / yli 2000 MHz
    (ekstrapoloitu), korkeus alle 10 m tai yli 1200 m ja etäisyys alle 1 km tai
    yli 1000 km (kiinnitetty reunaan).
    """
    if None in (freq_mhz, dist_km, h_ant_m):
        return False  # ei arvoa, ei väitettä
    f_ax, h_ax, d_ax = _axes()
    return not (
        f_ax[0] <= freq_mhz <= f_ax[-1]
        and h_ax[0] <= h_ant_m <= h_ax[-1]
        and d_ax[0] <= dist_km <= d_ax[-1]
    )


def _notice(row, geo, antennas, coord=()):
    """Yksi fxm_terra-rivi notice-rakenteeksi; (None, syy) kun pakollinen kenttä puuttuu.

    Teho: `pwr_dbw` on dBW. `pwr_eiv == "I"` on EIRP, joka muunnetaan ERP:iksi
    -2,15 dB:llä. Antennirivi valitaan deterministisesti: TX ja pienin `ant_key`.
    """
    terrakey = row.get("terrakey")
    freq_min, freq_max = _num(row.get("freq_min")), _num(row.get("freq_max"))
    if not terrakey or freq_min is None or freq_max is None:
        return None, "frequency"
    place = geo.get(row.get("geo_key"))
    lat, lon = (_num(place.get("lat_dec")), _num(place.get("long_dec"))) if place else (None, None)
    if lat is None or lon is None:
        return None, "location"
    cands = antennas.get(terrakey) or []
    if not cands:
        return None, "power"
    ant = min(cands, key=lambda a: _num(a.get("ant_key")) or 0)
    pwr_dbw = _num(ant.get("pwr_dbw"))
    if pwr_dbw is None:
        return None, "power"
    if ant.get("pwr_eiv") == "I":
        pwr_dbw -= 2.15
    return {
        "terrakey": terrakey,
        "adm_ref_id": row.get("adm_ref_id") or "",
        "adm": row.get("adm") or "?",
        "stn_cls": row.get("stn_cls") or "",
        "intent": row.get("intent") or "",
        "freq_min_mhz": freq_min,
        "freq_max_mhz": freq_max,
        "lat": lat,
        "lon": lon,
        "p_erp_kw": 10 ** (pwr_dbw / 10) / 1000,
        "ant_h_m": _num(ant.get("hgt_agl")),
        # fxm_terra.bdwdth on kHz (5000 = 5M00, 16.8 = 16K8).
        "bdwdth_khz": _num(row.get("bdwdth")),
        "prov": row.get("prov") or "",
        # fxm_coord-rivit: (coord_prov, adm, coord_st, src_status).
        "coord": [(c["coord_prov"], c["adm"], c["coord_st"], c["src_status"]) for c in coord],
    }, None


def load_issue_mdb(path):
    """Lukee yhden BR IFIC -MDB:n (fxm_terra + fxm_geo + fxm_ant + fxm_coord).

    Rivit, joilta puuttuu taajuus, sijainti tai teho, ohitetaan ja lasketaan
    syyn mukaan (`skipped_invalid`); puuttuvaa arvoa ei arvata. `intent_counts`
    lasketaan kaikista fxm_terra-riveistä: IFIC:n tila ei riipu siitä, pystyikö
    työkalu laskemaan rivin.

    Provenienssi (`file`, `sha256`, `path`) jaetaan `app.ingest`-moduulin kanssa:
    sama hash-funktio kuin avaruuspuolen ingestillä.
    """
    mdb = Path(path)
    if not mdb.is_file():
        raise ValueError(f"{mdb}: tiedostoa ei löytynyt")
    tables = {name: _export(mdb, name) for name in TABLES}
    geo = {row["geo_key"]: row for row in tables["fxm_geo"]}
    coord = {}
    for row in tables["fxm_coord"]:
        coord.setdefault(row["terrakey"], []).append(row)
    antennas = {}
    for row in tables["fxm_ant"]:
        if row["tx_rx"] == "TX":
            antennas.setdefault(row["terrakey"], []).append(row)
    notices, skipped = [], Counter()
    for row in tables["fxm_terra"]:
        notice, reason = _notice(row, geo, antennas, coord.get(row["terrakey"], ()))
        if notice is None:
            skipped[reason] += 1
        else:
            notices.append(notice)
    stem = mdb.stem
    return {
        "issue": stem[len("brific") :] if stem.startswith("brific") else stem,
        "file": mdb.name,
        "sha256": sha256(mdb),
        "path": mdb,
        "notices": notices,
        "intent_counts": dict(Counter(row["intent"] or "" for row in tables["fxm_terra"])),
        "skipped_invalid": dict(skipped),
    }


def band_label(notice):
    return f"{notice['freq_min_mhz']:g}-{notice['freq_max_mhz']:g} MHz"


def register_frequencies(path):
    """Suomen rekisterin taajuudet (MHz) molemmilta kanavanpuolilta.

    Molemmat suunnat, koska kanava on pari: RX 464.04 MHz ja TX 454.04 MHz
    ovat sama lupa, ja ilmoituksen kaista voi osua kumpaan tahansa.
    """
    freqs = []
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            for column in ("RX frequency", "TX frequency"):
                mhz = _mhz(row.get(column))
                if mhz:
                    freqs.append(mhz)
    if not freqs:
        raise ValueError(f"{path}: RX/TX-taajuussaraketta ei löytynyt")
    return freqs


def register_stations(path):
    """Suomen rekisterin asemat: tunnus, sijainti ja kanavan taajuudet.

    RX ensisijainen, TX fallback (Traficom Q&A 7.11.: jokainen TX vastaanotetaan
    Suomessa). Asemat, joilta puuttuu sijainti tai taajuus, ohitetaan; niitä ei
    arvata. `bw_khz` on kanavanleveys kynnyskorjausta varten.
    """
    stations = []
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            lat, lon = _num(row.get("Latitude")), _num(row.get("Longitude"))
            freqs = [
                m
                for m in (_mhz(row.get("RX frequency")), _mhz(row.get("TX frequency")))
                if m is not None
            ]
            if lat is None or lon is None or not freqs:
                continue
            stations.append(
                {
                    "station": (row.get("Station number") or "").strip(),
                    "lat": lat,
                    "lon": lon,
                    "freq_mhz": freqs[0],
                    "freqs_mhz": freqs,
                    "bw_khz": _khz(row.get("Channel bandwidth")),
                    "stn_cls": (row.get("Class of licence") or "").strip(),
                }
            )
    if not stations:
        raise ValueError(f"{path}: rekisteristä ei löytynyt asemia, joilla on sijainti")
    return stations


def diff_intents(curr):
    """Ilmoituksen tila `intent`-kentästä: IFIC ei ole kumulatiivinen kanta.

    Lukee `intent_counts`-kentän, joka lasketaan kaikista fxm_terra-riveistä,
    myös niistä joita ei voitu laskea. Palauttaa raa'at lukumäärät (`counts`)
    sekä muutosnimet (`new`/`modified`/`withdrawn`) ja kannan (`recorded`).
    """
    counts = Counter(curr["intent_counts"])
    summary = {change: counts[intent] for intent, change in INTENT_CHANGE.items()}
    summary["recorded"] = counts["RECORDED"]
    return {"counts": dict(counts), **summary}


def coord_fin(notice):
    """fxm_coord-rivit, joissa Suomi (FIN) on nimetty: 'provision status (src_status)'."""
    return sorted(
        {
            f"{prov}: {status} ({src})"
            for prov, adm, status, src in notice.get("coord") or ()
            if adm == "FIN"
        }
    )


def select(notices, register, max_km=MAX_DIST_KM):
    """Pitää ulkomaiset land-mobile-ilmoitukset < 1000 km päässä, jotka osuvat rekisteriin.

    Ilmoitus, jonka fxm_coord nimeää Suomen (FIN), pidetään aina: Suomi on silloin
    ilmoituksen oma koordinoitava hallinto, eikä rekisterin vajaus saa pudottaa sitä.
    Suomen omat ilmoitukset (adm FIN) jätetään pois.
    """
    kept, dropped = [], {"own": 0, "far": 0, "class": 0, "no_band_overlap": 0}
    for notice in notices:
        if notice["adm"] == "FIN":
            dropped["own"] += 1
            continue
        if coord_fin(notice):
            kept.append((notice, distance_to_border_km(notice["lat"], notice["lon"])))
            continue
        if notice["stn_cls"] not in LAND_MOBILE_CLASSES:
            dropped["class"] += 1
            continue
        distance = distance_to_border_km(notice["lat"], notice["lon"])
        if distance >= max_km:
            dropped["far"] += 1
            continue
        if not any(notice["freq_min_mhz"] <= f <= notice["freq_max_mhz"] for f in register):
            dropped["no_band_overlap"] += 1
            continue
        kept.append((notice, distance))
    return kept, dropped


def border_field_strength(freq_mhz, lat, lon, ant_h_m, p_erp_kw):
    """Kenttävoimakkuuden maksimi rajaviivalla, piste ja rajaosakohtaiset maksimit.

    Palauttaa (max_dbuv_m, (lat, lon), näytteiden lkm, extrapolated, sections,
    section, etäisyys maksimipisteeseen km). Kenttävoimakkuus lasketaan jokaisessa
    rajapisteessä ja raportoidaan suurin: se on rajaviivan kohta, jossa ulkomainen
    asema näkyy voimakkaimmin (Traficom 7.11.). `sections` on rajaosakohtainen
    maksimi, `section` on osa, jossa kokonaismaksimi syntyy (None jos ei arvoa).
    `extrapolated` koskee vain maksimipistettä: kaukainen näyte yli 1000 km ei
    vaikuta maksimiin eikä siten lippuun.
    """
    best, at, samples, best_dist, at_section = None, (None, None), 0, None, None
    sections = {}
    for blat, blon, section in border_samples():
        dist = haversine_km(lat, lon, blat, blon)
        value = field_strength_p1546(freq_mhz, dist, ant_h_m, p_erp_kw)
        samples += 1
        if value is not None:
            if best is None or value > best:
                best, at, best_dist, at_section = (
                    value,
                    (round(blat, 4), round(blon, 4)),
                    dist,
                    section,
                )
            if section not in sections or value > sections[section]:
                sections[section] = value
    extra = best_dist is not None and extrapolated(freq_mhz, best_dist, ant_h_m)
    return best, at, samples, extra, sections, at_section, best_dist


def _height(notice):
    """(laskentakorkeus, oletus tai None): ML ilman korkeutta saa ASSUMED_H1_M."""
    if notice["ant_h_m"] is not None and notice["ant_h_m"] > 0:
        return notice["ant_h_m"], None
    return ASSUMED_H1_M, (
        f"fxm_ant.hgt_agl missing: h1 assumed {ASSUMED_H1_M:g} m (lowest P.1546 table "
        "height, above a vehicle antenna, so the field strength is overestimated)"
    )


def _bandwidth(notice):
    """(kaistanleveys kHz, lähde): fxm_terra.bdwdth, muuten freq_max - freq_min."""
    if notice.get("bdwdth_khz"):
        return notice["bdwdth_khz"], "fxm_terra.bdwdth"
    return (notice["freq_max_mhz"] - notice["freq_min_mhz"]) * 1000, "freq_max - freq_min"


def _notice_finding(notice, distance, issue, register=()):
    centre = (notice["freq_min_mhz"] + notice["freq_max_mhz"]) / 2
    bw_khz, bw_source = _bandwidth(notice)
    h1, assumption = _height(notice)
    assumptions = [assumption] if assumption else []
    if h1 < ASSUMED_H1_M:
        assumptions.append(f"h1 {h1:g} m below 10 m: clamped to 10 m (overestimate)")
    e_max, at, samples, extra, sections, section, at_km = border_field_strength(
        centre, notice["lat"], notice["lon"], h1, notice["p_erp_kw"]
    )
    threshold = tr2508_threshold(centre, bw_khz)
    fin = coord_fin(notice)
    kept_because = []
    if any(notice["freq_min_mhz"] <= f <= notice["freq_max_mhz"] for f in register):
        kept_because.append("a Finnish register frequency falls in the notice band")
    if fin:
        kept_because.append(
            "Finland listed as affected administration (fxm_coord: " + "; ".join(fin) + ")"
        )
    # Tyhjän arvon syy näkyviin: tuntematon ei koskaan muutu 'ei koordinointia'.
    empty = {}
    if threshold is None:
        empty["threshold_dbuv_m"] = "no T/R 25-08 A1.2.3 row for this frequency (below 29.7 MHz)"
    if e_max is None:
        empty["border.max_dbuv_m"] = "P.1546 field strength not computable (power or distance)"
    undecided = threshold is None or e_max is None
    return {
        # Lähdeviite jokaiseen löydökseen: IFIC-numero, terrakey, adm, intent, taulut.
        "ific": issue,
        "terrakey": notice["terrakey"],
        "adm_ref_id": notice["adm_ref_id"],
        "adm": notice["adm"],
        "stn_cls": notice["stn_cls"],
        "intent": notice["intent"],
        "tables": list(TABLES),
        "band": band_label(notice),
        "tx_lat": notice["lat"],
        "tx_lon": notice["lon"],
        "notification_provision": notice.get("prov") or "",
        "coord_provisions": sorted({c[0] for c in notice.get("coord") or ()}),
        "coord_fin": bool(fin),
        "coord_fin_rows": fin,
        "kept_because": kept_because,
        "distance_to_border_km": round(distance, 1),
        "p_erp_kw": notice["p_erp_kw"],
        "ant_h_m": notice["ant_h_m"],
        "ant_h_used_m": h1,
        "assumptions": assumptions,
        "bandwidth_khz": bw_khz,
        "bandwidth_source": bw_source,
        "border": {
            "max_dbuv_m": None if e_max is None else round(e_max, 1),
            "at": at,
            "distance_km": None if at_km is None else round(at_km, 1),
            # Suurin arvo rajaosittain ja se osa, jossa kokonaismaksimi on.
            "section": section,
            "sections": {
                name: None if value is None else round(value, 1) for name, value in sections.items()
            },
            "samples": samples,
        },
        "extrapolated": extra,
        "threshold_dbuv_m": threshold,
        "margin_db": None if (e_max is None or threshold is None) else round(e_max - threshold, 1),
        # None = undecided (syy `empty_reason`-kentässä), ei koskaan False tuntemattomasta.
        "coordination": None if undecided else e_max >= threshold,
        "empty_reason": empty,
    }


def flag_stations(kept, stations):
    """Rekisterin suomalaiset asemat ja ulkomaisen kenttävoimakkuuden marginaali.

    Kenttävoimakkuus lasketaan aseman omassa sijainnissa (Traficom Q&A 7.11.), ei
    rajalla: sama P.1546-arvo kuin rajalla, mutta aseman kohdalla, ja verrataan
    T/R 25-08 -kynnykseen. Asemaa kohti raportoidaan voimakkain ilmoitus ja
    `exceeds`, kun kenttävoimakkuus ylittää kynnyksen. Kynnys jatkuu yli 470 MHz:n
    (Traficom 7.11.2026), joten yli 470 MHz:n ilmoitukset eivät enää ohita
    vertailua; `tr2508_threshold()` palauttaa niille 20 dB(uV/m).
    """
    worst = {}
    for notice, _ in kept:
        centre = (notice["freq_min_mhz"] + notice["freq_max_mhz"]) / 2
        threshold = tr2508_threshold(centre, _bandwidth(notice)[0])
        h1, assumption = _height(notice)
        if threshold is None:
            continue
        for station in stations:
            if not any(
                notice["freq_min_mhz"] <= f <= notice["freq_max_mhz"] for f in station["freqs_mhz"]
            ):
                continue
            distance = haversine_km(notice["lat"], notice["lon"], station["lat"], station["lon"])
            value = field_strength_p1546(centre, distance, h1, notice["p_erp_kw"])
            if value is None:
                continue
            entry = worst.get(station["station"])
            if entry is None or value > entry["e_dbuv_m"]:
                worst[station["station"]] = {
                    "station": station["station"],
                    "lat": station["lat"],
                    "lon": station["lon"],
                    "freq_mhz": station["freq_mhz"],
                    "stn_cls": station["stn_cls"],
                    "terrakey": notice["terrakey"],
                    "adm": notice["adm"],
                    "band": band_label(notice),
                    "distance_km": round(distance, 1),
                    "e_dbuv_m": round(value, 1),
                    "threshold_dbuv_m": threshold,
                    "margin_db": round(value - threshold, 1),
                    "exceeds": value >= threshold,
                    "assumption": assumption,
                }
    return sorted(worst.values(), key=lambda row: -row["margin_db"])


def _group_key(notice):
    width = notice["freq_max_mhz"] - notice["freq_min_mhz"]
    return (notice["adm"], band_label(notice), notice["stn_cls"], round(width, 3))


def trends(prev_notices, curr_notices):
    """Ryhmä (hallinto x kaista x luokka x kaistanleveys): muutokset vs. edellinen numero."""
    before = Counter(_group_key(n) for n in prev_notices)
    groups = {}
    for notice in curr_notices:
        change = INTENT_CHANGE.get(notice["intent"])
        if change is None:
            continue  # RECORDED on kanta, ei muutos
        group = groups.setdefault(_group_key(notice), {"new": 0, "modified": 0, "withdrawn": 0})
        group[change] += 1
    near = Counter()
    for notice in curr_notices:
        if distance_to_border_km(notice["lat"], notice["lon"]) < MAX_DIST_KM:
            near[_group_key(notice)] += 1
    rows = [
        {
            "neighbour": key[0] in NEIGHBOURS or near[key] > 0,
            "adm": key[0],
            "band": key[1],
            "stn_cls": key[2],
            "bw_mhz": key[3],
            "new": value["new"],
            "modified": value["modified"],
            "withdrawn": value["withdrawn"],
            "prev_count": before[key],
        }
        for key, value in groups.items()
    ]
    # Naapurit (NEIGHBOURS tai < 1000 km Suomen rajasta) ensin.
    rows.sort(
        key=lambda r: (
            not r["neighbour"],
            -(r["new"] + r["modified"]),
            r["adm"],
            r["band"],
            r["stn_cls"],
        )
    )
    return rows


def anomalies(rows, limit=5):
    """Naapuriryhmät, joilla ei ollut edellisessä issuessa ilmoituksia mutta nyt >= 3.

    Vain naapurihallinnot / < 1000 km Suomen rajasta; enintään `limit`, syy rivillä.
    """
    found = [r for r in rows if r["neighbour"] and r["prev_count"] == 0 and r["new"] >= 3]
    return [
        {
            **r,
            "reason": f"{r['adm']} {r['stn_cls']} {r['band']} ({r['bw_mhz']:g} MHz): "
            f"no notices in this group in the previous issue, {r['new']} new now",
        }
        for r in found[:limit]
    ]


def _source_block(issue):
    """Yhden luvun provenienssi samassa muodossa kuin avaruuskortin `source`."""
    return {
        "file": issue["file"],
        "sha256": issue["sha256"],
        "tables": list(TABLES),
        "keys": list(KEYS),
    }


def _threshold_block():
    return {
        "scheme": "ECC Recommendation T/R 25-08 (amended 28 September 2018), Annex 1 A1.2.3",
        "reference_bandwidth_khz": TR2508_REF_BW_KHZ,
        "time_percent": TIME_PERCENT,
        "location_percent": 50,
        "rx_height_m": RX_HEIGHT_M,
        "rows": [
            {"f_min_mhz": f_min, "f_max_mhz": f_max, "dbuv_m": dbuv}
            for f_min, f_max, dbuv in tr2508_rows()
        ],
        "bandwidth_correction": (
            "10*log10(bw/25 kHz) added when bw > 25 kHz; bw = fxm_terra.bdwdth, fallback "
            "freq_max - freq_min (per notice: bandwidth_khz, bandwidth_source)"
        ),
        "note": "model and threshold use the same 10 % time and 50 % locations",
    }


def findings(prev, curr, register_path):
    register = register_frequencies(register_path)
    stations = register_stations(register_path)
    kept, dropped = select(curr["notices"], register)
    notices = [
        _notice_finding(notice, distance, curr["issue"], register) for notice, distance in kept
    ]
    rows = trends(prev["notices"], curr["notices"])
    # The missing block describes the issue under evaluation (3076), not the baseline.
    skipped = Counter(curr.get("skipped_invalid") or {})
    audit = {
        # Sama provenienssi kuin avaruuskortilla: yksi tiiviste kaikista ajon syötteistä.
        "input_sha256": input_digest(
            [curr["path"], prev["path"], Path(register_path), RULES, BORDER, TR2508]
        ),
        "rules_version": RULES_VERSION,
        "run_at": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
    }
    flagged = flag_stations(kept, stations)
    return {
        "source": _source_block(curr),
        "prev_source": _source_block(prev),
        "issues": {"prev": prev["issue"], "curr": curr["issue"]},
        "model": "P.1546-6 land, 10 % time, 50 % locations, no terrain",
        "params": {
            "time_percent": TIME_PERCENT,
            "location_percent": 50,
            "rx_height_m": RX_HEIGHT_M,
            "interpolation": (
                "P.1546-6 Annex 5: log d (eq. 15), log h1 (eq. 8), log f (eq. 14, "
                "extrapolated below 100 / above 2000 MHz), capped at Efs (eq. 2); h1 < 10 m "
                "and h1 > 1200 m, d < 1 km and d > 1000 km clamped to the table edge"
            ),
            "assumed_h1_m_when_missing": ASSUMED_H1_M,
            "table": "rules/p1546_land.csv, generated by scripts/gen_p1546_table.py (Py1546)",
            "field_strength_for": (
                "frequency = band centre (freq_min+freq_max)/2, power = notice p_erp_kw, "
                "height = notice ant_h_m (ant_h_used_m when assumed), "
                "distance = direct distance to the border sample"
            ),
            "border_step_km": BORDER_STEP_KM,
        },
        "coordination_thresholds": _threshold_block(),
        "criterion": CRITERION,
        "border": {
            "source": (
                "Land borders: Natural Earth 50m admin-0 mainland ring; territorial sea "
                "outer limit: Marine Regions Finnish 12 NM (12 nautical miles). "
                "rules/finland_border.csv"
            ),
            "points": sum(len(line) for line in border_line()),
            "lines": len(border_line()),
            "samples": len(border_samples()),
            "step_km": BORDER_STEP_KM,
            # Rajaviiva on jaettu rajaosiin (`section`); nimet kertovat, minkä
            # naapurin vastaista rajaa tai aluevesirajaa osa edustaa.
            "sections": {
                name: SECTION_NAMES.get(name, name)
                for name in sorted({point[2] for line in border_line() for point in line})
            },
        },
        "audit": audit,
        "diff": diff_intents(curr),
        "notices": notices,
        "summary": {
            "in_reach": len(notices),
            "above_threshold": sum(n["coordination"] is True for n in notices),
            "undecided": sum(n["coordination"] is None for n in notices),
            "with_assumptions": sum(bool(n["assumptions"]) for n in notices),
            "coord_fin_kept": sum(n["coord_fin"] for n in notices),
        },
        "flagged_stations": {
            "count": sum(row["exceeds"] for row in flagged),
            "evaluated": len(flagged),
            "threshold_applied": True,
            "stations": flagged,
        },
        "trends": rows,
        "anomalies": anomalies(rows),
        # Sama kontrakti kuin avaruuskortin `missing`: mitä jäi lukematta. Kortilla
        # puuttuvat kenttänimet, täällä syyt ja rivimäärät, koska ilmoituksia on monta.
        "missing": dict(skipped),
        "missing_prev": dict(prev.get("skipped_invalid") or {}),
        "filter": {
            "max_distance_km": MAX_DIST_KM,
            "classes": sorted(LAND_MOBILE_CLASSES),
            "dropped": dropped,
        },
    }


def render_md(doc):
    sections_legend = ", ".join(f"{n} = {label}" for n, label in doc["border"]["sections"].items())
    lines = [
        "# TERRESTRIAL: BR IFIC -land-mobile-ilmoitukset",
        "",
        f"- lähde: `{doc['source']['file']}` sha256 `{doc['source']['sha256'][:16]}…` "
        f"(issu {doc['issues']['curr']})",
        f"- vertailupohja: `{doc['prev_source']['file']}` (issu {doc['issues']['prev']})",
        f"- ajo: {doc['audit']['run_at']}, säännöt {doc['audit']['rules_version']}",
        f"- taulut: {', '.join(TABLES)}",
        f"- mallinnus: {doc['model']}",
        f"- rajaviiva: {doc['border']['source']} ({doc['border']['points']} pistettä, "
        f"näyte {doc['border']['step_km']:g} km välein)",
        f"- rajaosat: {sections_legend}",
        f"- kehys: {doc['criterion']}",
        "",
        "## Koordinointikynnys (ECC T/R 25-08 A1.2.3)",
        "",
        f"25 kHz vertailukaista, {doc['coordination_thresholds']['time_percent']} % ajasta, "
        f"{doc['coordination_thresholds']['location_percent']} % paikoista, "
        f"{doc['coordination_thresholds']['rx_height_m']:g} m vastaanottoantenni. "
        "Kaistanleveyskorjaus 10*log10(bw/25 kHz), kun bw > 25 kHz; bw = fxm_terra.bdwdth "
        "(varalla freq_max - freq_min). Ilmoituskohtainen sovellettu kynnys korjauksineen "
        "on alla sarakkeessa 'kynnys'.",
        "",
        "| taajuus MHz | kynnys dB(uV/m) |",
        "|---|---|",
    ]
    for row in doc["coordination_thresholds"]["rows"]:
        lines.append(f"| {row['f_min_mhz']:g}-{row['f_max_mhz']:g} | {row['dbuv_m']:g} |")
    summary = doc["summary"]
    lines += [
        "",
        "## Kenttävoimakkuus rajaviivalla, dB(uV/m)",
        "",
        f"{summary['in_reach']} ilmoitusta ulottuvilla, {summary['above_threshold']} ylittää "
        f"kynnyksen, {summary['undecided']} ratkaisematta, {summary['coord_fin_kept']} pidetty "
        f"koska fxm_coord nimeää Suomen, {summary['with_assumptions']} oletuksella.",
        "",
        "| terrakey | hallinto | luokka | tila | kaista | lähetin lat, lon | etäisyys rajaan km "
        "| max rajalla | rajaosa | etäisyys maksimiin km | bw kHz (lähde) | kynnys | marginaali "
        "| koordinointi | huomiot |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for notice in doc["notices"]:
        border = notice["border"]
        e_max = "-" if border["max_dbuv_m"] is None else f"{border['max_dbuv_m']:.1f}"
        at_km = "-" if border["distance_km"] is None else f"{border['distance_km']:.0f}"
        section = border["section"] or "-"
        threshold = notice["threshold_dbuv_m"]
        threshold = "-" if threshold is None else f"{threshold:.1f}"
        margin = "-" if notice["margin_db"] is None else f"{notice['margin_db']:+.1f}"
        decision = {True: "kyllä", False: "ei", None: "ratkaisematta"}[notice["coordination"]]
        notes = [*notice["assumptions"], *notice["empty_reason"].values()]
        if notice["coord_fin"]:
            notes.append("fxm_coord nimeää FIN: " + "; ".join(notice["coord_fin_rows"]))
        if notice["extrapolated"]:
            notes.append("maksimipiste taulukon ulkopuolella")
        lines.append(
            f"| {notice['terrakey']} | {notice['adm']} | {notice['stn_cls']} "
            f"| {notice['intent']} | {notice['band']} "
            f"| {notice['tx_lat']:.4f}, {notice['tx_lon']:.4f} "
            f"| {notice['distance_to_border_km']:.0f} | {e_max} | {section} | {at_km} "
            f"| {notice['bandwidth_khz']:g} ({notice['bandwidth_source']}) "
            f"| {threshold} | {margin} | {decision} | {'; '.join(notes) or '-'} |"
        )
    if not doc["notices"]:
        lines.append("| - " * 15 + "|")
    lines += [
        "",
        "## Kenttävoimakkuus rajaosittain",
        "",
        "Voimakkain kenttävoimakkuus kussakin rajaosassa ja niiden ilmoitusten määrä,",
        "joiden maksimi osuu siihen (Traficom 7.11.2026: huomio rajaosiin, joissa",
        "kenttävoimakkuus voi olla suurin).",
        "",
        "| rajaosa | ilmoituksia, joiden maksimi | voimakkain dB(uV/m) |",
        "|---|---|---|",
    ]
    strongest = dict.fromkeys(doc["border"]["sections"])
    peaks = Counter()
    for notice in doc["notices"]:
        for name, value in notice["border"]["sections"].items():
            if value is not None and (strongest.get(name) is None or value > strongest[name]):
                strongest[name] = value
        if notice["border"]["section"]:
            peaks[notice["border"]["section"]] += 1
    for name in doc["border"]["sections"]:
        value = strongest[name]
        lines.append(f"| {name} | {peaks[name]} | {'-' if value is None else f'{value:.1f}'} |")
    lines += [
        "",
        "## Rekisterin asemat ulkomaista kenttävoimakkuutta vasten",
        "",
        f"Arvioitu {doc['flagged_stations']['evaluated']} asemaa, "
        f"{doc['flagged_stations']['count']} ylittää kynnyksen.",
        "",
    ]
    flagged = doc["flagged_stations"]["stations"]
    if flagged:
        lines += [
            "| asema | luokka | kaista | ilmoitus | hallinto | etäisyys km "
            "| kenttävoimakkuus | kynnys | marginaali | yli |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for row in flagged:
            lines.append(
                f"| {row['station']} | {row['stn_cls']} | {row['band']} | {row['terrakey']} "
                f"| {row['adm']} | {row['distance_km']:.0f} | {row['e_dbuv_m']:.1f} "
                f"| {row['threshold_dbuv_m']:.1f} | {row['margin_db']:+.1f} "
                f"| {'kyllä' if row['exceeds'] else 'ei'} |"
            )
    else:
        lines.append(
            "Ei arvioitavia asemia: yksikään ilmoitus ei osu rekisteriin T/R 25-08 -alueella."
        )
    neighbours = [row for row in doc["trends"] if row["neighbour"]]
    lines += [
        "",
        "## Trendit (naapurihallinnot)",
        "",
        f"Naapurit: {', '.join(sorted(NEIGHBOURS))} tai ilmoitus < {MAX_DIST_KM:g} km Suomen "
        f"rajasta; {len(neighbours)} ryhmää {len(doc['trends'])}:sta, alla 10 suurinta. Kaikki "
        "ryhmät: `terrestrial_trends.csv` (sarake `neighbour`, naapurit ensin).",
        "",
        "| hallinto | kaista | luokka | kaistanleveys MHz | uusi | muutettu | poistettu "
        "| edellinen |",
        "|---|---|---|---|---|---|---|---|",
    ]
    # shortcut: the headline shows the 10 largest neighbour groups; the CSV has every group.
    for row in neighbours[:10]:
        lines.append(
            f"| {row['adm']} | {row['band']} | {row['stn_cls']} | {row['bw_mhz']:g} "
            f"| {row['new']} | {row['modified']} | {row['withdrawn']} | {row['prev_count']} |"
        )
    lines += ["", "## Poikkeamat", ""]
    if doc["anomalies"]:
        for row in doc["anomalies"]:
            lines.append(f"- {row['reason']}")
    else:
        lines.append("Ei poikkeamia.")
    lines += ["", "## Rajaus", ""]
    lines.append(
        "Kenttävoimakkuus on laskennallinen arvio, ei mitattu: P.1546-6 maapolku ilman "
        "maastoa, 10 % ajasta ja 50 % paikoista, samat prosentit kuin T/R 25-08 A1.2.3 "
        "-kynnyksellä. ML-asemalle ilman antennikorkeutta oletetaan 10 m (yliarvio). "
        "Ilmoitus, jonka arvoa tai kynnystä ei voi laskea, on 'ratkaisematta', ei 'ei'. "
        "Kansallinen M4-kynnys on vahvistamatta."
    )
    return "\n".join(lines) + "\n"


def run(prev, curr, register_path, out_dir):
    doc = findings(prev, curr, register_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "terrestrial_findings.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (out / "terrestrial_trends.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "neighbour",
                "adm",
                "band",
                "stn_cls",
                "bw_mhz",
                "new",
                "modified",
                "withdrawn",
                "prev_count",
            ],
        )
        writer.writeheader()
        writer.writerows(doc["trends"])
    (out / "TERRESTRIAL.md").write_text(render_md(doc), encoding="utf-8")
    return doc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Terrestriaalinen diff ja P.1546-kenttävoimakkuus")
    parser.add_argument("--prev", required=True, help="edellinen BR IFIC -MDB (3075)")
    parser.add_argument("--curr", required=True, help="uusi BR IFIC -MDB (3076)")
    parser.add_argument("--register", required=True, help="Suomen rekisteri (CSV)")
    parser.add_argument("--out", default="out/", help="tulostehakemisto")
    args = parser.parse_args(argv)
    try:
        doc = run(load_issue_mdb(args.prev), load_issue_mdb(args.curr), args.register, args.out)
    except (OSError, ValueError) as error:
        raise SystemExit(f"terrestrial: {error}") from error
    print(
        f"{doc['diff']['new']} new, {doc['diff']['modified']} modified, "
        f"{doc['diff']['withdrawn']} withdrawn, {doc['diff']['recorded']} recorded; "
        f"{len(doc['notices'])} notices in reach; "
        f"{doc['flagged_stations']['count']} Finnish stations flagged; -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

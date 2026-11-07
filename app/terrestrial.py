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

Malli: ITU-R P.1546-6 maapolku, 50 % ajasta, 50 % paikoista, ei maastoa,
vastaanottoantenni 10 m. Taulukko `rules/p1546_land.csv` on generoitu ITU:n
hyväksymällä referenssitoteutuksella (eeveetza/Py1546, commit e235629):

    bt_loss(f, 50, h1, 10, 10, "Rural", [d], ["Land"], 0, 50, 0, 1, h1)[0]

taajuuksilla 100/600/2000 MHz, korkeuksilla 10/20/37.5/75/150/300/600/1200 m ja
P.1546:n nimellisetäisyyksillä 1–1000 km. Taulukon arvot ovat 1 kW ERP
-referenssille, joten teho lisätään 10*log10(p). Kysely interpoloidaan lineaarisesti
kaikilla kolmella akselilla ja kiinnittyy taulukon reunaan sen ulkopuolella.

Traficomin Q&A 7.11.2026: kenttävoimakkuus lasketaan **rajaviivan pisteissä**, ei
neljässä kaupungissa, ja lisäksi merkitään ne rekisterin suomalaiset asemat, joiden
kenttävoimakkuus ylittää koordinointikynnyksen. Rajaviiva on `rules/finland_border.csv`
(Natural Earth 50m, mantereen ulkorengas), jaettu `section`-sarakkeella rajaosiin sen
mukaan, minkä naapurin vastaista rajaa tai rannikkoa piste edustaa (SE, NO, RU, EE),
jotta tuloksesta näkyy, **missä osassa** kenttävoimakkuus on suurin (Traficom 7.11.).
Kynnys on CEPT/ECC T/R 25-08 A1.2.3
(`rules/tr2508_thresholds.csv`); Traficomin 7.11.2026 mukaan sama kriteeri jatkuu
yli 470 MHz:n, missä on 85 % aineiston maaliikenteen riveistä.
"""

import argparse
import csv
import io
import json
import math
import subprocess
from collections import Counter
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from app.config import RULES_VERSION
from app.ingest import input_digest, sha256

RULES = Path(__file__).resolve().parent.parent / "rules" / "p1546_land.csv"
BORDER = Path(__file__).resolve().parent.parent / "rules" / "finland_border.csv"
TR2508 = Path(__file__).resolve().parent.parent / "rules" / "tr2508_thresholds.csv"

# BR IFIC 3076 -skeeman taulut, joista notice rakennetaan.
TABLES = ("fxm_terra", "fxm_geo", "fxm_ant")
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
# Rajaosat (rules/finland_border.csv `section`): minkä naapurin vastaista rajaa tai
# rannikkoa kukin osa edustaa. Kolmipisteet Kilpisjärvi (SE/NO) ja Muotkavaara
# (NO/RU) sekä Suomenlahden rannikko (Viro) jakavat renkaan neljään osaan.
SECTION_NAMES = {
    "SE": "Ruotsi (Tornionlaakso, Perämeren–Saaristomeren rannikko)",
    "NO": "Norja (Käsivarsi)",
    "RU": "Venäjä (itäraja)",
    "EE": "Viro (Suomenlahden rannikko)",
}
# Traficom 7.11.2026: T/R 25-08 päättyy 470 MHz:iin, ja sen yläpuolella sovelletaan
# samaa kriteeriä kuin 400-470 MHz:n alueella (20 dB(uV/m) + kaistanleveyskorjaus).
# Ilman tätä 85 % 3076:n maaliikenteen riveistä jäisi ilman kynnystä.
CRITERION = (
    "protection framework in three tiers: "
    "ITU RR Art. 21 Table 21-4 (PFD limit, the level the space path applies) -> "
    "CEPT/ECC T/R 25-08 A1.2.3 (coordination threshold at the border line, "
    "25 kHz reference bandwidth, 10 % time, 10 m receiving antenna; Traficom "
    "7.11.2026 applies the 400-470 MHz criterion above 470 MHz) applies here -> "
    "national M4 / Traficomin taajuusjakotaulukko (protection threshold to be confirmed)"
)
# T/R 25-08:n kynnys on määritelty 10 % ajasta; käytössä oleva P.1546-taulukko on
# 50 % ajasta, joten ylitys on aina varma mutta alitus ei todista mitään (T8).
TIME_PERCENT_NOTE = (
    "the exceedance flag uses the P.1546-6 50 % time value against the 10 % time "
    "threshold, so a flagged station is a definite exceedance while a low value "
    "does not prove the threshold is met"
)


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
    """Suomen rajaviiva suljettuna murtoviivana (lat, lon, section).

    `section` = rajaosa sen mukaan, minkä naapurin vastaista rajaa tai rannikkoa
    piste edustaa: SE (Tornionlaakso ja Perämeren–Saaristomeren rannikko Ruotsia
    vasten), NO (Norjan raja), RU (Venäjän raja), EE (Suomenlahden rannikko Viroa
    vasten). Neljä osaa kattavat koko renkaan. Rajat on merkitty kolmen
    kolmipisteen (Kilpisjärvi, Muotkavaara) ja Suomenlahden rannikon kohdalle.
    """
    points = []
    with BORDER.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            points.append((float(row["lat"]), float(row["lon"]), row["section"]))
    if len(points) < 3:
        raise ValueError(f"{BORDER}: rajaviiva tarvitsee vähintään 3 pistettä")
    return tuple(points)


@lru_cache(maxsize=1)
def border_samples():
    """Rajaviiva tasavälein (`BORDER_STEP_KM`): kenttävoimakkuuden laskentapisteet.

    Jokainen näyte kantaa sen janan rajaosan, jolla se on, joten maksimi voidaan
    laskea rajaosittain.
    """
    ring = border_line()
    samples = []
    for i in range(len(ring)):
        a, b = ring[i], ring[(i + 1) % len(ring)]
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


def distance_to_border_km(lat, lon):
    """Lyhin etäisyys Suomen rajaviivaan, ei neljään testipisteeseen (T2)."""
    ring = border_line()
    return min(
        _point_segment_km(lat, lon, ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring))
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


def _bracket(axis, x):
    """(ala, ylä, paino); taulukon ulkopuolella kiinnittyy lähimpään pisteeseen."""
    if x <= axis[0]:
        return axis[0], axis[0], 0.0
    if x >= axis[-1]:
        return axis[-1], axis[-1], 0.0
    for lo, hi in zip(axis, axis[1:], strict=False):
        if lo <= x <= hi:
            return lo, hi, (x - lo) / (hi - lo)
    raise AssertionError("akseli ei ole järjestyksessä")


def field_strength_p1546(freq_mhz, dist_km, h_ant_m, p_erp_kw):
    """Kenttävoimakkuus dB(uV/m): P.1546-6 maapolku, 50/50, ei maastoa.

    Lineaarinen interpolointi taajuudessa, antennikorkeudessa ja etäisyydessä.
    Palauttaa None, jos syöte ei ole fysikaalinen (esim. etäisyys 0).
    """
    if None in (freq_mhz, dist_km, h_ant_m, p_erp_kw):
        return None
    if dist_km <= 0 or p_erp_kw <= 0 or h_ant_m <= 0 or freq_mhz <= 0:
        return None
    grid = _grid()
    f_ax, h_ax, d_ax = _axes()
    f_lo, f_hi, wf = _bracket(f_ax, float(freq_mhz))
    h_lo, h_hi, wh = _bracket(h_ax, float(h_ant_m))
    d_lo, d_hi, wd = _bracket(d_ax, float(dist_km))
    e = 0.0
    for f, w_f in ((f_lo, 1 - wf), (f_hi, wf)):
        for h, w_h in ((h_lo, 1 - wh), (h_hi, wh)):
            for d, w_d in ((d_lo, 1 - wd), (d_hi, wd)):
                e += w_f * w_h * w_d * grid[(f, h, d)]
    return e + 10 * math.log10(p_erp_kw)


def extrapolated(freq_mhz, dist_km, h_ant_m):
    """Onko kysely taulukon ulkopuolella (arvo kiinnittyy reunapisteeseen).

    Kaikki kolme akselia, molemmin puolin: matala taajuus, korkea antenni ja lyhyt
    etäisyys kiinnittyvät siinä missä korkea taajuus tai pitkä etäisyys.
    """
    if None in (freq_mhz, dist_km, h_ant_m):
        return False  # ei arvoa, ei väitettä
    f_ax, h_ax, d_ax = _axes()
    return not (
        f_ax[0] <= freq_mhz <= f_ax[-1]
        and h_ax[0] <= h_ant_m <= h_ax[-1]
        and d_ax[0] <= dist_km <= d_ax[-1]
    )


def _export(mdb, table):
    """Yksi taulu `mdb-export`illa (sama lukija kuin scripts/fetch_data.py)."""
    result = subprocess.run(
        ["mdb-export", str(mdb), table], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise ValueError(f"{mdb}: mdb-export {table} epäonnistui: {result.stderr.strip()}")
    return list(csv.DictReader(io.StringIO(result.stdout)))


def _notice(row, geo, antennas):
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
    }, None


def load_issue_mdb(path):
    """Lukee yhden BR IFIC -MDB:n (fxm_terra + fxm_geo + fxm_ant).

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
    antennas = {}
    for row in tables["fxm_ant"]:
        if row["tx_rx"] == "TX":
            antennas.setdefault(row["terrakey"], []).append(row)
    notices, skipped = [], Counter()
    for row in tables["fxm_terra"]:
        notice, reason = _notice(row, geo, antennas)
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


def select(notices, register, max_km=MAX_DIST_KM):
    """Pitää land-mobile-ilmoitukset, jotka ovat < 1000 km päässä ja osuvat rekisteriin."""
    kept, dropped = [], {"far": 0, "class": 0, "no_band_overlap": 0}
    for notice in notices:
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
    section). Kenttävoimakkuus lasketaan jokaisessa rajapisteessä ja raportoidaan
    suurin: se on rajaviivan kohta, jossa ulkomainen asema näkyy voimakkaimmin
    (Traficom 7.11.). `sections` on rajaosakohtainen maksimi (None = ei arvoa
    osassa), `section` on osa, jossa kokonaismaksimi syntyy (None jos ei arvoa).
    """
    best, at, samples, extra = None, (None, None), 0, False
    sections = {}
    for blat, blon, section in border_samples():
        dist = haversine_km(lat, lon, blat, blon)
        value = field_strength_p1546(freq_mhz, dist, ant_h_m, p_erp_kw)
        samples += 1
        if value is not None:
            if best is None or value > best:
                best, at = value, (round(blat, 4), round(blon, 4))
            if section not in sections or value > sections[section]:
                sections[section] = value
        extra = extra or extrapolated(freq_mhz, dist, ant_h_m)
    at_section = next((s for s, v in sections.items() if v == best), None)
    return best, at, samples, extra, sections, at_section


def _notice_finding(notice, distance, issue):
    centre = (notice["freq_min_mhz"] + notice["freq_max_mhz"]) / 2
    bw_khz = (notice["freq_max_mhz"] - notice["freq_min_mhz"]) * 1000
    e_max, at, samples, extra, sections, section = border_field_strength(
        centre, notice["lat"], notice["lon"], notice["ant_h_m"], notice["p_erp_kw"]
    )
    threshold = tr2508_threshold(centre, bw_khz)
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
        "distance_to_border_km": round(distance, 1),
        "p_erp_kw": notice["p_erp_kw"],
        "ant_h_m": notice["ant_h_m"],
        "border": {
            "max_dbuv_m": None if e_max is None else round(e_max, 1),
            "at": at,
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
        "coordination": None if threshold is None else (e_max is not None and e_max >= threshold),
    }


def flag_stations(kept, stations):
    """Rekisterin suomalaiset asemat ja ulkomaisen kenttävoimakkuuden marginaali.

    Kenttävoimakkuus lasketaan aseman omassa sijainnissa (Traficom Q&A 7.11.), ei
    rajalla: sama P.1546-arvo kuin rajalla, mutta aseman kohdalla, ja verrataan
    T/R 25-08 -kynnykseen. Asemaa kohti raportoidaan voimakkain ilmoitus ja
    `exceeds`, kun kenttävoimakkuus ylittää kynnyksen. Ilmoitukset taajuusalueen
    ulkopuolella (yli 470 MHz) ohitetaan, koska T/R 25-08 ei aseta niille kynnystä.
    """
    worst = {}
    for notice, _ in kept:
        centre = (notice["freq_min_mhz"] + notice["freq_max_mhz"]) / 2
        bw_khz = (notice["freq_max_mhz"] - notice["freq_min_mhz"]) * 1000
        threshold = tr2508_threshold(centre, bw_khz)
        if threshold is None:
            continue
        for station in stations:
            if not any(
                notice["freq_min_mhz"] <= f <= notice["freq_max_mhz"] for f in station["freqs_mhz"]
            ):
                continue
            distance = haversine_km(notice["lat"], notice["lon"], station["lat"], station["lon"])
            value = field_strength_p1546(centre, distance, notice["ant_h_m"], notice["p_erp_kw"])
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
    rows = [
        {
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
    rows.sort(key=lambda r: (-(r["new"] + r["modified"]), r["adm"], r["band"], r["stn_cls"]))
    return rows


def anomalies(rows, limit=5):
    """Ryhmä, jolla ei ollut edellisessä issuessa yhtään ilmoitusta mutta nyt vähintään 3."""
    found = [row for row in rows if row["prev_count"] == 0 and row["new"] >= 3]
    return found[:limit]


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
        "time_percent": 10,
        "location_percent": 50,
        "rx_height_m": RX_HEIGHT_M,
        "rows": [
            {"f_min_mhz": f_min, "f_max_mhz": f_max, "dbuv_m": dbuv}
            for f_min, f_max, dbuv in tr2508_rows()
        ],
        "note": TIME_PERCENT_NOTE,
    }


def findings(prev, curr, register_path):
    register = register_frequencies(register_path)
    stations = register_stations(register_path)
    kept, dropped = select(curr["notices"], register)
    notices = [_notice_finding(notice, distance, curr["issue"]) for notice, distance in kept]
    rows = trends(prev["notices"], curr["notices"])
    skipped = Counter(prev.get("skipped_invalid") or {}) + Counter(
        curr.get("skipped_invalid") or {}
    )
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
        "model": "P.1546-6 land, 50/50, no terrain",
        "params": {
            "rx_height_m": RX_HEIGHT_M,
            "field_strength_for": (
                "frequency = band centre (freq_min+freq_max)/2, power = notice p_erp_kw, "
                "height = notice ant_h_m, distance = direct distance to the border sample"
            ),
            "border_step_km": BORDER_STEP_KM,
        },
        "coordination_thresholds": _threshold_block(),
        "criterion": CRITERION,
        "border": {
            "source": (
                "Natural Earth 50m admin-0 mainland ring (public domain), rules/finland_border.csv"
            ),
            "points": len(border_line()),
            "samples": len(border_samples()),
            "step_km": BORDER_STEP_KM,
            # Rajaviiva on jaettu rajaosiin (`section`); nimet kertovat, minkä
            # naapurin vastaista rajaa tai rannikkoa osa edustaa.
            "sections": {
                name: SECTION_NAMES.get(name, name) for name in sorted(p[2] for p in border_line())
            },
        },
        "audit": audit,
        "diff": diff_intents(curr),
        "notices": notices,
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
        f"{doc['coordination_thresholds']['rx_height_m']:g} m vastaanottoantenni.",
        "",
        "| taajuus MHz | kynnys dB(uV/m) |",
        "|---|---|",
    ]
    for row in doc["coordination_thresholds"]["rows"]:
        lines.append(f"| {row['f_min_mhz']:g}-{row['f_max_mhz']:g} | {row['dbuv_m']:g} |")
    lines += [
        "",
        "## Kenttävoimakkuus rajaviivalla, dB(uV/m)",
        "",
        "| terrakey | hallinto | tila | kaista | etäisyys km | max rajalla | rajaosa "
        "| kynnys | marginaali |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for notice in doc["notices"]:
        border = notice["border"]
        e_max = "-" if border["max_dbuv_m"] is None else f"{border['max_dbuv_m']:.1f}"
        section = border["section"] or "-"
        threshold = notice["threshold_dbuv_m"]
        threshold = "-" if threshold is None else f"{threshold:.1f}"
        margin = "-" if notice["margin_db"] is None else f"{notice['margin_db']:+.1f}"
        lines.append(
            f"| {notice['terrakey']} | {notice['adm']} | {notice['intent']} | {notice['band']} "
            f"| {notice['distance_to_border_km']:.0f} | {e_max} | {section} "
            f"| {threshold} | {margin} |"
        )
    if not doc["notices"]:
        lines.append("| - | - | - | - | - | - | - | - | - |")
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
    lines += [
        "",
        "## Trendit",
        "",
        "| hallinto | kaista | luokka | kaistanleveys MHz | uusi | muutettu | poistettu "
        "| edellinen |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in doc["trends"]:
        lines.append(
            f"| {row['adm']} | {row['band']} | {row['stn_cls']} | {row['bw_mhz']:g} "
            f"| {row['new']} | {row['modified']} | {row['withdrawn']} | {row['prev_count']} |"
        )
    lines += ["", "## Poikkeamat", ""]
    if doc["anomalies"]:
        for row in doc["anomalies"]:
            lines.append(
                f"- {row['adm']} {row['band']}: ei ilmoituksia edellisessä issuessa, "
                f"nyt {row['new']}."
            )
    else:
        lines.append("Ei poikkeamia.")
    lines += ["", "## Rajaus", ""]
    lines.append(
        "Kenttävoimakkuus on laskennallinen arvio, ei mitattu. Ylitys on varma, mutta "
        "alitus ei todista, että kynnys alittuu: P.1546-taulukko on 50 % ajasta ja kynnys "
        "on määritelty 10 % ajasta (T/R 25-08 A1.2.3). Kansallinen M4-kynnys on nimeämättä."
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

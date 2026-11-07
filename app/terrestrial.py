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

# BR IFIC 3076 -skeeman taulut, joista notice rakennetaan.
TABLES = ("fxm_terra", "fxm_geo", "fxm_ant")
# Tulosteen `source.keys`: mistä taulujen avaimista luku tuli (SCOPE 7, sama kontrakti
# kuin avaruuskortin `ntc_id` / `grp_id` / `beam_name`).
KEYS = ("terrakey", "adm_ref_id")
# intent -> muutoksen nimi. RECORDED on kanta, ei muutos.
INTENT_CHANGE = {"ADD": "new", "MODIFY": "modified", "SUPPRESS": "withdrawn"}

# Neljä suomalaista testipistettä. Samat pisteet toimivat kenttävoimakkuuden
# mittauspisteinä ja "etäisyys Suomeen" -suodattimen ankkureina.
POINTS = {
    "Helsinki": (60.1699, 24.9384),
    "Turku": (60.4518, 22.2666),
    "Lappeenranta": (61.0587, 28.1887),
    "Maarianhamina": (60.0971, 19.9348),
}
MAX_DIST_KM = 1000.0
RX_HEIGHT_M = 10.0
# BR IFIC -asemaluokat: FB = tukiasema, ML = maaliikenne, FL = maaliikenne (kiinteä).
LAND_MOBILE_CLASSES = frozenset({"FB", "ML", "FL"})
# Traficom ei ole nimennyt kenttävoimakkuutta, jolla suojelu käynnistyy: työkalu raportoi
# lasketun arvon eikä väitä ylitystä eikä alitusta sen sijaan että keksisi kynnyksen (T5).
THRESHOLD_DBUV_M = None  # asetetaan vasta kun Traficom nimeää suojelukriteerin
CRITERION = (
    "protection framework in three tiers: "
    "ITU RR Art. 21 Table 21-4 (PFD limit, the level the space path applies) -> "
    "CEPT/ECC T/R 25-08 (field strength that triggers protection, no value confirmed) -> "
    "national M4 / Traficomin taajuusjakotaulukko (protection threshold to be confirmed)"
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


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def distance_to_finland_km(lat, lon):
    """Lähin testipiste. Dokumentoitu korvike maantieteelliselle rajalle."""
    return min(haversine_km(lat, lon, *point) for point in POINTS.values())


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
        distance = distance_to_finland_km(notice["lat"], notice["lon"])
        if distance >= max_km:
            dropped["far"] += 1
            continue
        if not any(notice["freq_min_mhz"] <= f <= notice["freq_max_mhz"] for f in register):
            dropped["no_band_overlap"] += 1
            continue
        kept.append((notice, distance))
    return kept, dropped


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


def findings(prev, curr, register_path):
    register = register_frequencies(register_path)
    kept, dropped = select(curr["notices"], register)
    notices = []
    for notice, distance in kept:
        centre = (notice["freq_min_mhz"] + notice["freq_max_mhz"]) / 2
        points = {}
        extrapolated_any = False
        for name, (lat, lon) in POINTS.items():
            point_km = haversine_km(notice["lat"], notice["lon"], lat, lon)
            value = field_strength_p1546(centre, point_km, notice["ant_h_m"], notice["p_erp_kw"])
            points[name] = {
                "dist_km": round(point_km, 1),
                "e_dbuv_m": None if value is None else round(value, 1),
            }
            extrapolated_any = extrapolated_any or extrapolated(centre, point_km, notice["ant_h_m"])
        notices.append(
            {
                # Lähdeviite jokaiseen löydökseen: IFIC-numero, terrakey, adm, intent, taulut.
                "ific": curr["issue"],
                "terrakey": notice["terrakey"],
                "adm_ref_id": notice["adm_ref_id"],
                "adm": notice["adm"],
                "stn_cls": notice["stn_cls"],
                "intent": notice["intent"],
                "tables": list(TABLES),
                "band": band_label(notice),
                "distance_to_finland_km": round(distance, 1),
                "p_erp_kw": notice["p_erp_kw"],
                "ant_h_m": notice["ant_h_m"],
                "points": points,
                "extrapolated": extrapolated_any,
            }
        )
    rows = trends(prev["notices"], curr["notices"])
    skipped = Counter(prev.get("skipped_invalid") or {}) + Counter(
        curr.get("skipped_invalid") or {}
    )
    audit = {
        # Sama provenienssi kuin avaruuskortilla: yksi tiiviste kaikista ajon syötteistä.
        "input_sha256": input_digest([curr["path"], prev["path"], Path(register_path), RULES]),
        "rules_version": RULES_VERSION,
        "run_at": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
    }
    return {
        "source": _source_block(curr),
        "prev_source": _source_block(prev),
        "issues": {"prev": prev["issue"], "curr": curr["issue"]},
        "model": "P.1546-6 land, 50/50, no terrain",
        "params": {
            "rx_height_m": RX_HEIGHT_M,
            "field_strength_for": (
                "frequency = band centre (freq_min+freq_max)/2, power = notice p_erp_kw, "
                "height = notice ant_h_m, distance = direct distance to the point"
            ),
        },
        "protection_threshold_dbuVm": THRESHOLD_DBUV_M,
        "criterion": CRITERION,
        "audit": audit,
        "diff": diff_intents(curr),
        "notices": notices,
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
    lines = [
        "# TERRESTRIAL: BR IFIC -land-mobile-ilmoitukset",
        "",
        f"- lähde: `{doc['source']['file']}` sha256 `{doc['source']['sha256'][:16]}…` "
        f"(issu {doc['issues']['curr']})",
        f"- vertailupohja: `{doc['prev_source']['file']}` (issu {doc['issues']['prev']})",
        f"- ajo: {doc['audit']['run_at']}, säännöt {doc['audit']['rules_version']}",
        f"- taulut: {', '.join(TABLES)}",
        f"- mallinnus: {doc['model']}",
        f"- suojelukynnys: `{doc['protection_threshold_dbuVm']}`",
        f"- kehys: {doc['criterion']}",
        "",
        "## Ilmoituksen tila (intent)",
        "",
        "| intent | muutos | lkm |",
        "|---|---|---|",
    ]
    for intent, change in (*INTENT_CHANGE.items(), ("RECORDED", "kanta")):
        lines.append(f"| {intent} | {change} | {doc['diff']['counts'].get(intent, 0)} |")
    lines += [
        "",
        f"Uudet {doc['diff']['new']}, muutetut {doc['diff']['modified']}, "
        f"poistetut {doc['diff']['withdrawn']}, kanta {doc['diff']['recorded']}.",
        "",
        "## Kenttävoimakkuus suomalaisissa testipisteissä, dB(uV/m)",
        "",
        "| terrakey | hallinto | tila | kaista | " + " | ".join(POINTS) + " |",
        "|---|---|---|---|" + "---|" * len(POINTS),
    ]
    for notice in doc["notices"]:
        cells = [
            "-" if p["e_dbuv_m"] is None else f"{p['e_dbuv_m']:.1f}"
            for p in notice["points"].values()
        ]
        head = (
            f"| {notice['terrakey']} | {notice['adm']} | {notice['intent']} | {notice['band']} | "
        )
        lines.append(head + " | ".join(cells) + " |")
    if not doc["notices"]:
        lines.append("| - | - | - | - | " + " | ".join("-" for _ in POINTS) + " |")
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
        "Kenttävoimakkuus on laskennallinen arvio, ei mitattu. Ilman nimettyä "
        "suojelukynnystä työkalu ei väitä ylitystä eikä alitusta."
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
        f"{len(doc['notices'])} notices in reach; -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

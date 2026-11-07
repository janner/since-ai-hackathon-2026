"""Turn cases into the case card, the queue and the output files.

Every number in a card comes from the case; the prose modules may only restate them.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

from app import prose
from app.allocation import m4_lookup
from app.config import (
    ADM_NAMES,
    DIRECTIVE_GAIN_DB,
    NTF_REASONS,
    THRESHOLD_NOTE,
    fmt_date,
    fmt_mhz,
    fmt_num,
    regulatory_stage,
)
from app.gates import Case, GateResult
from app.ingest import IficData

GEOMETRY_FIELDS = ("bore_long", "bore_lat", "maj_axis", "min_axis")
REGISTER_GAIN = "frequencies_of_interest.Ant gain (dB)"
REGISTER_POWER = "frequencies_of_interest.Radioation power"
SYNTHETIC_POWER_W = 1e9  # above 1 GW the value is a synthetic artefact (plan 3.6)
# Traficom Q&A Q3: beams are not assessed individually, the worst case is always assumed.
WORST_CASE = "worst case assumed: peak beam gain toward the Finnish territory"


def _regulatory_stage(notice) -> dict:
    """The stage a filing stands in, for the card and the queue."""
    stage = regulatory_stage(notice.prov)
    return {key: stage[key] for key in ("provision", "label", "source", "rank")}


def _threshold_note(victim) -> str | None:
    """A directive, high-gain station may be protected at a lower level: say so, change nothing."""
    if (
        victim is not None
        and victim.gain_db is not None
        and victim.gain_db >= DIRECTIVE_GAIN_DB
        and victim.directivity != "ND"
    ):
        return THRESHOLD_NOTE
    return None


def build_card(case: Case, ific: IficData, m4_rows: list[dict], audit: dict) -> dict:
    notice = ific.notices[case.ntc_id]
    beam = ific.beam(case.ntc_id, case.beam)
    geometry = beam.geometry if beam is not None else {}
    victim = case.victim
    return {
        "case_id": f"{ifact_tag(ific)}-{case.ntc_id}",
        "same_network": ific.same_network(case.ntc_id),
        "source": {
            "file": ific.file,
            "ific": ifact_tag(ific),
            # The run's input digest; the terrestrial path carries the same key in
            # its own `source` block. Same contract, different calculation path.
            "sha256": audit["input_sha256"],
            "tables": ["notice", "freq", "emiss", "s_beam", "geo", "orbit", "ntc_lnk", "grp_res35"],
            "keys": {"ntc_id": case.ntc_id, "grp_id": case.grp_id, "beam_name": case.beam},
        },
        "parties": {
            "admin": notice.adm,
            "network_org": notice.ntwk_org,
            "adm_ref_id": notice.adm_ref_id,
        },
        "band": {
            "freq_min_mhz": case.band_lo_mhz,
            "freq_max_mhz": case.band_hi_mhz,
            "bandwidth_mhz": round(case.band_hi_mhz - case.band_lo_mhz, 2),
        },
        "direction": "space-to-Earth",
        "coverage": {
            "orbit": case.orbit,
            "sat_name": ific.sat_name(case.ntc_id),
            "longitude_deg": _longitude(ific, case.ntc_id),
            "elevation_deg": case.elev_deg,
            "beam": case.beam,
            "beam_geometry": "missing" if _missing_geometry(geometry) else "declared",
            "coverage_hint": f"beam name {case.beam}; {WORST_CASE}",
        },
        "point": {
            "lat": case.lat,
            "lon": case.lon,
            "place": case.place or "any point in Finland (the pass sweeps every elevation)",
        },
        "victim": (
            {
                "station": victim.id,
                "class": victim.licence,
                "lat": victim.lat,
                "lon": victim.lon,
                "rx_mhz": victim.rx_mhz,
                "gain_db": victim.gain_db,
                "power_w": victim.power_w,
                "direction_deg": victim.direction_deg,
                "directivity": victim.directivity,
            }
            if victim is not None
            else None
        ),
        "synthetic_data_warning": (
            "victim received power is above 1 GW (synthetic register artefact); "
            "the value is shown but not used in the PFD calculation"
            if victim is not None
            and victim.power_w is not None
            and victim.power_w > SYNTHETIC_POWER_W
            else None
        ),
        "calculation": {
            "method": "PFD_peak_upper_bound",
            "psd_dbw_hz": case.psd_dbw_hz,
            "beam_gain_db": case.beam_gain_db,
            "distance_km": case.slant_km,
            "fspl_db": case.fspl_db,
            "pfd_dbw_m2_hz": case.pfd_dbw_m2_hz,
            "limit_dbw_m2_hz": case.limit_dbw_m2_hz,
            "margin_db": case.margin_db,
            "limit_source": case.limit.cite(),
            "offset_db": case.offset_db,
            "perigee_km": case.perigee_km,
        },
        "m4": m4_lookup(m4_rows, case.band_lo_mhz, case.band_hi_mhz),
        "class": case.klass,
        "adjacent": case.adjacent,
        "deadline": fmt_date(case.deadline) if case.deadline else None,
        "deadline_passed": case.deadline_passed,
        "regulatory_stage": _regulatory_stage(notice),
        "filing_action": notice.act_code,
        "filing_follows": [
            {"ntc_id": link.ntc_id, "reason": link.reason}
            for link in ific.links.get(case.ntc_id, [])
        ],
        "threshold_note": _threshold_note(victim),
        "missing": missing_fields(case, geometry),
        "next_action": {
            "counterparty": notice.adm,
            "template": "templates/correspondence_fi_en.md",
            "question": (
                f"Can {ADM_NAMES.get(notice.adm, notice.adm)} confirm the worst-case PFD the "
                f"{ific.sat_name(case.ntc_id)} {case.beam} beam produces on Finnish territory "
                f"in the {fmt_mhz(case.band_lo_mhz)}-{fmt_mhz(case.band_hi_mhz)} MHz range?"
            ),
        },
        "audit": {
            "input_sha256": audit["input_sha256"],
            "rules_version": audit["rules_version"],
            "run_at": audit["run_at"],
        },
    }


def ifact_tag(ific: IficData) -> str:
    """'ific3074.mdb' -> '3074': the short name used in case_id."""
    digits = "".join(c for c in ific.file if c.isdigit())
    return digits or "ific"


def missing_fields(case: Case, geometry: dict) -> list[str]:
    missing = [f"s_beam.{key}" for key in GEOMETRY_FIELDS if geometry.get(key) is None]
    if case.victim is not None and case.victim.gain_db is None:
        missing.append(REGISTER_GAIN)
    if case.victim is not None and case.victim.power_w is None:
        missing.append(REGISTER_POWER)
    return missing


def _longitude(ific: IficData, ntc_id: str) -> float | None:
    geo = ific.geo.get(ntc_id)
    return geo.long_nom if geo is not None else None


def _missing_geometry(geometry: dict) -> bool:
    return all(geometry.get(key) is None for key in GEOMETRY_FIELDS)


def _blocking(missing: list[str]) -> list[str]:
    """Missing fields that matter: beam geometry does not, the worst case covers it (Q3)."""
    return [field for field in missing if not field.startswith("s_beam.")]


def deadline_lines(card: dict) -> list[str]:
    """The Resolution 35 line, or none. A passed deadline is marked, never hidden."""
    if not card.get("deadline"):
        return []
    passed = " (passed)" if card.get("deadline_passed") else ""
    return [f"- **Resolution 35 deadline:** {card['deadline']}{passed}"]


def render_card_md(card: dict) -> str:
    calc, band, victim = card["calculation"], card["band"], card["victim"] or {}
    stage = card["regulatory_stage"]
    point = card["point"]
    marker = " — adjacent" if card["adjacent"] else ""
    where = (
        f"{fmt_num(point['lat'])} N {fmt_num(point['lon'])} E ({point['place']})"
        if point.get("lat") is not None and point.get("lon") is not None
        else point["place"]
    )
    lines = [
        f"# {card['case_id']} — {card['class']}{marker}",
        "",
        f"- **Satellite:** {card['coverage']['sat_name']} ({card['coverage']['orbit']}, "
        f"{card['parties']['admin']}), beam {card['coverage']['beam']}",
        f"- **Band:** {fmt_mhz(band['freq_min_mhz'])}-{fmt_mhz(band['freq_max_mhz'])} MHz",
        f"- **Stage:** {stage['provision']} — {stage['label']}",
        *deadline_lines(card),
        f"- **Point:** {where}, elevation {fmt_num(card['coverage']['elevation_deg'])}°",
        f"- **PFD:** {fmt_num(calc['pfd_dbw_m2_hz'])} dB(W/m²/Hz) vs limit "
        f"{fmt_num(calc['limit_dbw_m2_hz'])} dB(W/m²/Hz) → margin {fmt_num(calc['margin_db'])} dB",
        f"- **Limit:** {calc['limit_source']}",
        f"- **Finland allocation:** {card['m4']['services_in_finland']}"
        + ("" if card["m4"]["satellite_use"] else " (no satellite service)"),
    ]
    for link in card["filing_follows"]:
        reason = NTF_REASONS.get(link["reason"], link["reason"])
        lines.append(f"- This filing follows {link['ntc_id']} ({reason})")
    if victim.get("station"):
        bits = [f"station {victim['station']} ({victim['class']})"]
        if victim.get("directivity") in ("D", "ND"):
            bits.append("directive" if victim["directivity"] == "D" else "non-directive")
        if victim.get("gain_db") is not None:
            bits.append(f"{fmt_num(victim['gain_db'])} dBi")
        lines.append(f"- **Reference:** {', '.join(bits)}")
    lines += [
        f"- **Coverage:** {card['coverage']['coverage_hint']}",
        f"- **Missing:** {', '.join(_blocking(card['missing'])) or 'nothing'}",
    ]
    if card["threshold_note"]:
        lines.append(f"- **Threshold:** {card['threshold_note']}")
    lines += [f"- **Question:** {card['next_action']['question']}", ""]
    return "\n".join(lines)


def render_cases_md(cards: list[dict]) -> str:
    head = f"# Cases ({len(cards)})\n\n"
    return head + "\n".join(render_card_md(card) for card in cards)


def render_queue_md(result: GateResult) -> str:
    counts = result.counts
    tiers = _tier_counts(result)
    head = (
        f"# Queue ({len(result.queue)} notices: {tiers['attention']} need attention, "
        f"{tiers['checked']} checked, {tiers['no_effect']} without effect on Finland)\n\n"
        f"Funnel: {counts['notices']} → {counts['g1']} → {counts['g2']} → "
        f"{counts['g3']} + {counts['cannot_decide']}\n\n"
        f"Every notice in the package has a row here. The ones that need attention come first; "
        f"the rest stay visible with their reason.\n\n"
    )
    header = (
        "| # | case | class | stage | action | deadline | margin dB | Finland band | "
        "settles at | reason |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
    )
    parts = [head, f"## Needs attention ({tiers['attention']})\n\n", header]
    parts.append(
        "\n".join(
            f"| {index} | {item.ntc_id} | {item.klass} | {item.stage} | "
            f"{item.filing_action or '-'} | {_deadline_cell(item)} | "
            f"{'-' if item.margin_db is None else fmt_num(item.margin_db)} | "
            f"{item.band_use or '-'} | {_settles(item)} | {item.reason} |"
            for index, item in enumerate(_tier(result, "attention"), start=1)
        )
    )
    parts.append(f"\n\n## Checked, nothing to note ({tiers['checked']})\n\n{header}")
    parts.append(
        "\n".join(
            f"| {index} | {item.ntc_id} | {item.klass} | {item.stage} | "
            f"{item.filing_action or '-'} | {_deadline_cell(item)} | "
            f"{'-' if item.margin_db is None else fmt_num(item.margin_db)} | "
            f"{item.band_use or '-'} | {_settles(item)} | {item.reason} |"
            for index, item in enumerate(_tier(result, "checked"), start=1)
        )
    )
    parts.append(
        f"\n\n## No effect on Finland ({tiers['no_effect']})\n\n"
        "| # | case | stage | reason |\n|---|---|---|---|\n"
    )
    parts.append(
        "\n".join(
            f"| {index} | {item.ntc_id} | {item.stage or '-'} | {item.reason} |"
            for index, item in enumerate(_tier(result, "no_effect"), start=1)
        )
    )
    note = (
        "\n\n`settles at` is the value the missing field would need to reach the Table 21-4 limit: "
        "a PSD in dBW/Hz, a beam gain in dBi. It comes from `margin = psd + gain - fspl - limit`, "
        "solved for the missing term at margin 0, so it is an exact bound and not a search "
        "result. `deadline` is the notice's earliest upcoming Resolution 35 deadline "
        "(`grp_res35`); a passed one is marked, and `-` means no group of the notice carries one. "
        "A `not_space` reason names the part of the band where Finland has no satellite "
        "allocation: one such part is enough, because the use of the frequency is what is "
        "protected.\n"
    )
    return "".join(parts) + note


def _tier(result: GateResult, tier: str) -> list:
    return [item for item in result.queue if item.tier == tier]


def _tier_counts(result: GateResult) -> dict[str, int]:
    counts = {"attention": 0, "checked": 0, "no_effect": 0}
    for item in result.queue:
        counts[item.tier] = counts.get(item.tier, 0) + 1
    return counts


def _deadline_cell(item) -> str:
    """The queue's deadline cell: the date, a passed one marked, or `-`."""
    if item.deadline is None:
        return "-"
    passed = " (passed)" if item.deadline_passed else ""
    return f"{fmt_date(item.deadline)}{passed}"


def _settles(item) -> str:
    """The value the missing field would need for the case to reach the limit."""
    if item.required_db is None:
        return "-"
    unit = "dBW/Hz" if item.unknown_field == "psd" else "dBi"
    return f"{item.unknown_field} ≥ {fmt_num(item.required_db)} {unit}"


def funnel_json(result: GateResult) -> dict:
    return {
        "input_sha256": result.input_sha256,
        "rules_version": result.rules_version,
        "run_at": result.run_at,
        "mode": result.mode,
        "counts": result.counts,
        "drops": result.drops,
        "queue": {"shown": len(result.queue), **_tier_counts(result)},
        "undecided_detail": {
            ntc_id: {"reason": result.undecided[ntc_id], "field": field, "required_db": value}
            for ntc_id, (field, value) in result.required.items()
        },
    }


def results_rows(result: GateResult, ific: IficData, cards: list[dict]) -> list[dict]:
    """One row per notice in the input, dropped notices with their reason code."""
    by_id = {card["case_id"]: card for card in cards}
    rows = []
    for ntc_id, notice in ific.notices.items():
        case = result.case_by_id().get(ntc_id)
        stage, drop_reason = result.dropped.get(ntc_id, ("", ""))
        reason = drop_reason or result.undecided.get(ntc_id, "")
        card = by_id.get(f"{ifact_tag(ific)}-{ntc_id}")
        rows.append(
            {
                "ific": ifact_tag(ific),
                "case_id": card["case_id"] if card else "",
                "ntc_id": ntc_id,
                "adm": notice.adm,
                "sat_name": ific.sat_name(ntc_id),
                "ntc_type": notice.ntc_type,
                "orbit": case.orbit if case is not None else "",
                "dropped_at": stage,
                "reason": reason,
                "class": case.klass
                if case is not None
                else ("" if stage else ("cannot_decide" if reason else "")),
                "regulatory_stage": regulatory_stage(notice.prov)["provision"],
                "freq_min_mhz": case.band_lo_mhz if case is not None else "",
                "freq_max_mhz": case.band_hi_mhz if case is not None else "",
                "bandwidth_mhz": (
                    round(case.band_hi_mhz - case.band_lo_mhz, 2) if case is not None else ""
                ),
                "station": case.victim.id if case is not None and case.victim else "",
                "lat": case.lat if case is not None else "",
                "lon": case.lon if case is not None else "",
                "victim_rx_mhz": case.victim.rx_mhz if case is not None and case.victim else "",
                "elevation_deg": case.elev_deg if case is not None else "",
                "pfd_dbw_m2_hz": case.pfd_dbw_m2_hz if case is not None else "",
                "limit_dbw_m2_hz": case.limit_dbw_m2_hz if case is not None else "",
                "margin_db": case.margin_db if case is not None else "",
                "limit_source": case.limit.cite() if case is not None else "",
                "m4_services": card["m4"]["services_in_finland"] if card else "",
                "m4_space": (
                    "yes" if case is not None and case.band_satellite else ("no" if case else "")
                ),
                "missing": ";".join(card["missing"]) if card else "",
            }
        )
    return rows


RESULT_COLUMNS = (
    "ific",
    "case_id",
    "ntc_id",
    "adm",
    "sat_name",
    "ntc_type",
    "orbit",
    "dropped_at",
    "reason",
    "class",
    "regulatory_stage",
    "freq_min_mhz",
    "freq_max_mhz",
    "bandwidth_mhz",
    "station",
    "lat",
    "lon",
    "victim_rx_mhz",
    "elevation_deg",
    "pfd_dbw_m2_hz",
    "limit_dbw_m2_hz",
    "margin_db",
    "limit_source",
    "m4_services",
    "m4_space",
    "missing",
)


def render_run_log(
    result: GateResult, counts: dict[str, int], ific: IficData, letters: int = 0
) -> str:
    return "\n".join(
        [
            f"run_at={result.run_at}",
            f"input_sha256={result.input_sha256}",
            f"rules_version={result.rules_version}",
            f"ific={ifact_tag(ific)}",
            f"source_file={ific.file}",
            f"mode={result.mode}",
            f"notices={result.counts['notices']}",
            f"freq_rows={counts.get('freq', 0)}",
            f"register_rows={result.reference_stations}",
            f"territory_points={len(result.places)}",
            f"bands={len(result.bands)}",
            f"visible=GEO {result.geo_visible} NGSO {result.ngso_visible}",
            f"g1={result.counts['g1']} g2={result.counts['g2']} g3={result.counts['g3']} "
            f"cannot_decide={result.counts['cannot_decide']}",
            f"letters={letters}",
            f"elapsed_s={result.elapsed_s:.2f}",
            "",
        ]
    )


def write_outputs(
    result: GateResult,
    ific: IficData,
    cards: list[dict],
    counts: dict[str, int],
    out: Path,
) -> None:
    out.mkdir(parents=True, exist_ok=True)
    letters = [card for card in cards if card["class"] == "exceeds"]
    letters_dir = out / "letters"
    (out / "cases.json").write_text(
        json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "cases.md").write_text(render_cases_md(cards), encoding="utf-8")
    (out / "queue.md").write_text(render_queue_md(result), encoding="utf-8")
    (out / "funnel.json").write_text(
        json.dumps(funnel_json(result), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "run.log").write_text(
        render_run_log(result, counts, ific, len(letters)), encoding="utf-8"
    )
    with (out / f"{ifact_tag(ific)}_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        writer.writerows(results_rows(result, ific, cards))
    # A run owns out/letters: regenerate it so a stale letter from an earlier mode cannot
    # outlive the cases of this run. Only cases above the limit get one (the brief's last step).
    if letters_dir.exists():
        shutil.rmtree(letters_dir)
    letters_dir.mkdir()
    for card in letters:
        (letters_dir / f"{card['case_id']}.md").write_text(
            prose.draft_letter(card)["text"], encoding="utf-8"
        )

"""Is the notified band a satellite allocation in Finland?

The allocation table (M4) is the baseline. A band is satellite use when any overlapping row
names a satellite service, in either direction: an uplink or an inter-satellite allocation is
still a satellite allocation, so it does not make the band "not satellite use". Only a band
with a Finnish allocation and no satellite service at all is the finding.

The Excel register is a reference, not the allocation: it lists the stations someone chose to
hand over, and the authorities do not disclose all use. A band that is not a satellite
allocation in M4 is a finding on its own, whatever the PFD says.
"""

from __future__ import annotations

from app.config import M4_SERVICES, M4_SOURCE, M4_SUB_HI, M4_SUB_LO


def satellite_use(service: str) -> bool:
    """Does this service name include a satellite service, in any direction?"""
    return "SATELLITE" in service.upper()


def finnish_bands(m4_rows: list[dict]) -> list[tuple[float, float]]:
    """The whole Finnish allocation as merged (lo, hi) MHz intervals."""
    spans = sorted(
        (row[M4_SUB_LO] / 1e6, row[M4_SUB_HI] / 1e6)
        for row in m4_rows
        if M4_SUB_LO in row and M4_SUB_HI in row
    )
    merged: list[list[float]] = []
    for lo_mhz, hi_mhz in spans:
        if merged and lo_mhz <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi_mhz)
        else:
            merged.append([lo_mhz, hi_mhz])
    return [(lo_mhz, hi_mhz) for lo_mhz, hi_mhz in merged]


def segments(m4_rows: list[dict], lo_mhz: float, hi_mhz: float) -> list[dict]:
    """The notified band split at every M4 sub-band edge, each piece with its own answer.

    A piece is covered by a row only when the row contains the whole piece, so a band edge
    that merely touches a row does not borrow that row's services.
    """
    lo_hz, hi_hz = lo_mhz * 1e6, hi_mhz * 1e6
    cuts = {lo_hz, hi_hz}
    for row in m4_rows:
        row_lo = row.get(M4_SUB_LO, 0)
        row_hi = row.get(M4_SUB_HI, 0)
        if row_lo < hi_hz and row_hi > lo_hz:
            cuts.add(max(row_lo, lo_hz))
            cuts.add(min(row_hi, hi_hz))
    edges = sorted(cuts)
    found: list[dict] = []
    for low, high in zip(edges, edges[1:], strict=False):
        if high <= low:
            continue
        hits = [
            row for row in m4_rows if row.get(M4_SUB_LO, 0) <= low and row.get(M4_SUB_HI, 0) >= high
        ]
        services = sorted({str(row.get(M4_SERVICES, "")).strip() for row in hits} - {""})
        found.append(
            {
                "lo_mhz": round(low / 1e6, 3),
                "hi_mhz": round(high / 1e6, 3),
                "services": services,
                "satellite": any(satellite_use(service) for service in services),
                "m4_row_ids": [row["ID"] for row in hits if "ID" in row][:8],
            }
        )
    return found


def m4_lookup(m4_rows: list[dict], lo_mhz: float, hi_mhz: float) -> dict:
    """The M4 allocation over the notified band, and the parts of it without a satellite use.

    The check is per sub-band, not per notice: a notice at 3 625-4 200 MHz covers MOBILE AND
    FIXED only from 3 625 to 3 800 MHz, so one part without a satellite allocation makes the
    whole notice a finding. The customer protects the use of the frequency, and that part has
    none.
    """
    parts = segments(m4_rows, lo_mhz, hi_mhz)
    services = sorted({service for part in parts for service in part["services"]})
    gaps = [(part["lo_mhz"], part["hi_mhz"]) for part in parts if not part["satellite"]]
    if not parts:
        return {
            "rows": [],
            "band_mhz": [],
            "services_in_finland": "not allocated",
            "satellite_use": False,
            "gaps": [(lo_mhz, hi_mhz)],
            "segments": [],
            "source": M4_SOURCE,
        }
    hits = [
        row
        for row in m4_rows
        if row.get(M4_SUB_LO, 0) < hi_mhz * 1e6 and row.get(M4_SUB_HI, 0) > lo_mhz * 1e6
    ]
    ids = [row["ID"] for row in hits if "ID" in row]
    return {
        "rows": [min(ids), max(ids)] if ids else [],
        "band_mhz": (
            [
                min(row[M4_SUB_LO] for row in hits) / 1e6,
                max(row[M4_SUB_HI] for row in hits) / 1e6,
            ]
            if hits
            else [lo_mhz, hi_mhz]
        ),
        "services_in_finland": ", ".join(services) if services else "not allocated",
        "satellite_use": not gaps,
        "gaps": gaps,
        "segments": parts,
        "source": M4_SOURCE,
    }

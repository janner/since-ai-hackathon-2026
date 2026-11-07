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


def m4_lookup(m4_rows: list[dict], lo_mhz: float, hi_mhz: float) -> dict:
    """The M4 allocation sub-bands that overlap the notified band."""
    lo_hz, hi_hz = lo_mhz * 1e6, hi_mhz * 1e6
    hits = [
        row for row in m4_rows if row.get(M4_SUB_LO, 0) <= hi_hz and row.get(M4_SUB_HI, 0) >= lo_hz
    ]
    if not hits:
        return {
            "rows": [],
            "band_mhz": [],
            "services_in_finland": "not allocated",
            "satellite_use": False,
            "source": M4_SOURCE,
        }
    ids = [row["ID"] for row in hits if "ID" in row]
    services = sorted({str(row.get(M4_SERVICES, "")).strip() for row in hits})
    services = [service for service in services if service]
    return {
        "rows": [min(ids), max(ids)] if ids else [],
        "band_mhz": [
            min(row[M4_SUB_LO] for row in hits) / 1e6,
            max(row[M4_SUB_HI] for row in hits) / 1e6,
        ],
        "services_in_finland": ", ".join(services),
        "satellite_use": any(satellite_use(service) for service in services),
        "source": M4_SOURCE,
    }

"""Is the notified band a satellite allocation in Finland?

A downlink needs a satellite service with the space-to-Earth direction in Finland's own
allocation table (Traficom M4). The table also lists uplinks and inter-satellite links;
neither licenses a downlink, so they do not make a band "satellite use in Finland".

The Excel register is a reference, not the allocation: it lists the stations someone chose
to hand over, and the authorities do not disclose all use. The allocation table is the
baseline, and a band that is not a satellite allocation there is a finding on its own,
whatever the PFD says.
"""

from __future__ import annotations

from app.config import M4_SERVICES, M4_SOURCE, M4_SUB_HI, M4_SUB_LO


def space_to_earth(service: str) -> bool:
    """Does this service name allow a downlink?"""
    text = service.upper()
    if "SATELLITE" not in text or "INTER-SATELLITE" in text:
        return False
    # No direction named: the allocation covers both, as in "EARTH EXPLORATION-SATELLITE".
    return "SPACE-TO-EARTH" in text or "EARTH-TO-SPACE" not in text


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
            "space_to_earth": False,
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
        "space_to_earth": any(space_to_earth(service) for service in services),
        "source": M4_SOURCE,
    }

"""Static configuration for Kaista.

The seven bands below are the reference set for `app.bands` (the register's own bands, F2);
the full run's scope is every Finnish allocation, derived from M4 at run time (D18), and the
demo slice is config. No protected band is hardcoded from the register anywhere in this repo.
"""

from __future__ import annotations

from datetime import date

# The reference bands for `app.bands`, the register's own-band question (F2). The run's full
# scope comes from M4 (`app.allocation.finnish_bands`), not from this list.
SPACE_BANDS_MHZ: tuple[tuple[float, float], ...] = (
    (3470.0, 3780.0),
    (5900.0, 6400.0),
    (7250.0, 8400.0),
    (9400.0, 9900.0),
    (10700.0, 13250.0),
    (17300.0, 20200.0),
    (25200.0, 27500.0),
)

# The demo slice: the only group where the register also carries the calculation fields.
DEMO_SLICE_MHZ: tuple[float, float] = (3470.0, 3780.0)

RULES_VERSION = "1.1.0"

# Classification of the worst-case margin.
EXCEEDS_DB = 0.0
NEAR_DB = -3.0

# Adjacent-channel guard, in MHz. 0.0 keeps G1 at plain band overlap (the default: it keeps
# the run comparable). Raise it when Traficom confirms a channel-spacing threshold; a case
# that only enters through the guard is marked adjacent and is capped at class `near`, because
# the Table 21-4 limit does not apply outside the notified band.
GUARD_MHZ = 0.0

# A register station this directive (gain at or above this, and not non-directional) can be
# protected at a lower trigger level; the card says so but changes no number and no class.
DIRECTIVE_GAIN_DB = 20.0
THRESHOLD_NOTE = (
    "the station has a directive antenna; the trigger level may be lower if the source is in "
    "the main beam direction"
)

# The regulatory stage carried in notice.prov (ITU RR 2024 Vol 1). `rank` orders the queue: a
# stage another administration can still influence (advance publication, coordination request)
# comes before a filing already recorded in the MIFR.
REGULATORY_STAGES = {
    "9.1/IA": {
        "provision": "No. 9.1",
        "label": "advance publication; another administration can still influence the filing",
        "source": "ITU RR 2024, Vol 1, No. 9.1",
        "rank": 0,
    },
    "9.6": {
        "provision": "No. 9.6",
        "label": "coordination request; another administration can still influence the filing",
        "source": "ITU RR 2024, Vol 1, No. 9.6",
        "rank": 0,
    },
    "11.2": {
        "provision": "No. 11.2",
        "label": "notification recorded in the MIFR",
        "source": "ITU RR 2024, Vol 1, No. 11.2",
        "rank": 1,
    },
    "RS49": {
        "provision": "Resolution 49",
        "label": "Resolution 49 filing",
        "source": "ITU RR 2024, Vol 1, Resolution 49",
        "rank": 2,
    },
}

M4_SOURCE = "opendata.traficom.fi/api/v13/Taajuusjakotaulukko"

# ntc_lnk.lnkntf_rsn: the nature of the notice a filing follows. The code set is the same as
# notice.ntf_rsn, which pairs one-to-one with notice.prov in IFIC 3074, so the labels are the
# stage labels above. A code outside the set is shown as it stands, never guessed.
NTF_REASONS = {
    "N": "notification, No. 11.2",
    "C": "coordination request, No. 9.6",
    "A": "advance publication, No. 9.1",
    "U": "Resolution 49 filing",
}

# Table of frequency allocations (M4) sub-band columns, in Hz.
M4_SUB_LO = "Sub_band_lower_limit__Hz_"
M4_SUB_HI = "Sub_band_upper_limit__Hz_"
M4_SERVICES = "Services_in_Finland"

# Only the code names needed for the one-line question in the correspondence template.
ADM_NAMES = {"CHN": "China", "USA": "the United States", "RUS": "Russia", "EST": "Estonia"}


def fmt_mhz(value: float) -> str:
    """3400.0 -> '3 400' (Finnish thousands separator); 3662.5 -> '3 662,5'."""
    text = f"{value:,.1f}".rstrip("0").rstrip(".")
    return text.replace(",", "\u00a0").replace(".", ",")


def fmt_num(value: float) -> str:
    """-184.78 -> '-184,78' (Finnish decimal comma)."""
    return f"{value:g}".replace(".", ",")


def fmt_date(value: date) -> str:
    """date(2026, 12, 19) -> '19.12.2026' (Finnish day-first order)."""
    return value.strftime("%d.%m.%Y")


def regulatory_stage(prov: str) -> dict:
    """notice.prov -> the stage dict, with a last-place fallback for an unknown provision."""
    known = REGULATORY_STAGES.get(prov)
    if known is not None:
        return known
    return {
        "provision": prov or "unknown",
        "label": "unknown provision",
        "source": "",
        "rank": len(REGULATORY_STAGES),
    }

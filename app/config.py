"""Static configuration for Kaista.

The seven space bands below are the ITU space allocations the challenge covers; they are
config, not data. The *protected* bands themselves are always derived from the Finnish
register (see app.bands) -- no channel frequency is hardcoded anywhere in this repo.
"""

from __future__ import annotations

# ITU space allocations (MHz) that the Finnish register is screened against.
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

QUEUE_CAP = 20
RULES_VERSION = "1.1.0"

# Classification of the worst-case margin.
EXCEEDS_DB = 0.0
NEAR_DB = -3.0

M4_SOURCE = "opendata.traficom.fi/api/v13/Taajuusjakotaulukko"

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

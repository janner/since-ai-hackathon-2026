"""Finnish territory as the points the PFD is evaluated at.

The border file holds the land borders (SE, NO, RU) and the territorial sea outer limit (TS),
the two edges Traficom named in the Q&A. The register's stations are inside that area, so a
worst case taken only at their locations understates the level at the edge.

Worst case over an area sits on its edge: the slant range grows as the ground point moves away
from the sub-satellite point, the free-space loss grows with the range, and the Table 21-4
limit does not rise faster than the range loss. So the vertices are enough; no polygon and no
grid. A vertex spacing of at most about 0.5 degrees moves an elevation by well under 0.1 dB.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

BORDER = Path(__file__).resolve().parent.parent / "rules" / "finland_border.csv"
SECTIONS = {
    "SE": "land border, Sweden",
    "NO": "land border, Norway",
    "RU": "land border, Russia",
    "TS": "territorial sea outer limit",
}


@dataclass(frozen=True)
class Place:
    lat: float
    lon: float
    section: str

    @property
    def label(self) -> str:
        return SECTIONS.get(self.section, self.section)


@lru_cache(maxsize=1)
def places(path: Path = BORDER) -> tuple[Place, ...]:
    """The territory edge, one vertex per point, in file order."""
    found: list[Place] = []
    seen: set[tuple[str, str, str]] = set()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (row["section"], row["lat"], row["lon"])
            if key in seen:
                continue
            seen.add(key)
            found.append(Place(float(row["lat"]), float(row["lon"]), row["section"].strip()))
    return tuple(found)

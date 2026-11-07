"""Statistics over the complaint ledger: what was complained about, who, and what was done.

Every number comes from the events in `app.ledger`; there is no language model and no stored
aggregate. The shape is the one the "Tilastot" section of the UI draws, and `csv_rows()` flattens
the same rows for Excel.
"""

from __future__ import annotations

from app.config import fmt_mhz
from app.ledger import complaints, load, median_days

SECTIONS = ("admins", "networks", "bands", "issues", "actions")


def band_label(item: dict) -> str:
    band = item.get("band") or {}
    lo, hi = band.get("freq_min_mhz"), band.get("freq_max_mhz")
    if lo is None or hi is None:
        return "unknown"
    return f"{fmt_mhz(lo)}-{fmt_mhz(hi)} MHz"


def matching(
    items: list[dict],
    *,
    year: int | None = None,
    adm: str | None = None,
    sat_name: str | None = None,
    band: str | None = None,
    issue_type: str | None = None,
    status: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> list[dict]:
    """Narrow the complaints: only the filters actually given change anything."""
    out = items
    if year is not None:
        out = [i for i in out if i["at"][:4] == str(year)]
    if start:
        out = [i for i in out if i["at"][:10] >= start]
    if end:
        out = [i for i in out if i["at"][:10] <= end]
    if adm:
        out = [i for i in out if i["adm"] == adm]
    if sat_name:
        out = [i for i in out if i["sat_name"] == sat_name]
    if issue_type:
        out = [i for i in out if i["issue_type"] == issue_type]
    if status:
        out = [i for i in out if i["status"] == status]
    if band:
        out = [i for i in out if band_label(i) == band]
    return out


def _counts(items: list[dict], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = item.get(field)
        if key:
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _group(items: list[dict], key, meta: tuple = ()) -> list[dict]:
    """One row per distinct value of `key` (a field name or a function): how many, how many still
    open, how they ended."""

    def value_of(item: dict) -> str:
        value = key(item) if callable(key) else item.get(key)
        return str(value) if value else ""

    buckets: dict[str, list[dict]] = {}
    for item in items:
        value = value_of(item)
        if value:
            buckets.setdefault(value, []).append(item)
    rows = []
    for value, group in buckets.items():
        row = {
            "key": value,
            "count": len(group),
            "open": sum(1 for i in group if i["status"] == "open"),
            "repeat": len(group) >= 2,
            "median_days": median_days(group),
            "outcomes": _counts(group, "outcome"),
        }
        # The first row of the group carries the identity fields the UI shows next to the label.
        for field in meta:
            row[field] = group[0].get(field)
        rows.append(row)
    return sorted(rows, key=lambda row: (-row["count"], row["key"]))


def _actions(items: list[dict]) -> list[dict]:
    """What was done: one row per recorded action, with how those complaints ended."""
    buckets: dict[str, list[dict]] = {}
    for item in items:
        for action in item["actions"]:
            buckets.setdefault(action, []).append(item)
    rows = [
        {
            "key": action,
            "count": len(group),
            "open": sum(1 for i in group if i["status"] == "open"),
            "repeat": False,
            "median_days": median_days(group),
            "outcomes": _counts(group, "outcome"),
        }
        for action, group in buckets.items()
    ]
    return sorted(rows, key=lambda row: (-row["count"], row["key"]))


def _trend(items: list[dict]) -> list[dict]:
    years: dict[str, list[dict]] = {}
    for item in items:
        years.setdefault(item["at"][:4], []).append(item)
    rows = []
    for year, group in years.items():
        quarters = {
            f"q{quarter}": sum(1 for i in group if (int(i["at"][5:7]) - 1) // 3 == quarter - 1)
            for quarter in range(1, 5)
        }
        rows.append({"year": year, "total": len(group), **quarters})
    return sorted(rows, key=lambda row: row["year"])


def summarize(items: list[dict]) -> dict:
    """The three questions in one object: what (bands/issues), who (admins/networks), what was done."""
    letters = sum(len(i["letters"]) for i in items)
    return {
        "totals": {
            "complaints": len(items),
            "open": sum(1 for i in items if i["status"] == "open"),
            "closed": sum(1 for i in items if i["status"] == "closed"),
            "synthetic": sum(1 for i in items if i["synthetic"]),
            "letters": letters,
            "without_action": sum(1 for i in items if not i["actions"]),
            "median_days": median_days(items),
        },
        "admins": _group(items, "adm"),
        "networks": _group(items, "sat_name", meta=("network_org",)),
        "bands": _group(items, band_label),
        "issues": _group(items, "issue_type"),
        "actions": _actions(items),
        "trend": _trend(items),
    }


def csv_rows(summary: dict) -> list[dict]:
    """The same rows as the UI shows, flattened for Excel: one line per table row."""
    rows = []
    for section in SECTIONS:
        for row in summary[section]:
            rows.append(
                {
                    "section": section,
                    "key": row["key"],
                    "count": row["count"],
                    "open": row["open"],
                    "repeat": row["repeat"],
                    "median_days": row["median_days"] if row["median_days"] is not None else "",
                    "outcomes": "; ".join(f"{k}={v}" for k, v in row["outcomes"].items()),
                    "network_org": row.get("network_org", ""),
                }
            )
    for row in summary["trend"]:
        rows.append(
            {
                "section": "trend",
                "key": row["year"],
                "count": row["total"],
                "open": "",
                "repeat": "",
                "median_days": "",
                "outcomes": "; ".join(f"{k}={row[k]}" for k in ("q1", "q2", "q3", "q4")),
                "network_org": "",
            }
        )
    return rows


def report(
    directory=None,
    synthetic: bool = True,
    *,
    year: int | None = None,
    adm: str | None = None,
    sat_name: str | None = None,
    band: str | None = None,
    issue_type: str | None = None,
    status: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> tuple[dict, list[dict]]:
    """Read the ledger, filter it and summarize it. Returns (summary, the filtered complaints)."""
    items = matching(
        complaints(load(synthetic=synthetic, directory=directory)),
        year=year,
        adm=adm,
        sat_name=sat_name,
        band=band,
        issue_type=issue_type,
        status=status,
        start=start,
        end=end,
    )
    return summarize(items), items

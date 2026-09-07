"""
socrates_client.py
--------------------
Fetches REAL conjunction screening results from CelesTrak's SOCRATES Plus
service instead of reimplementing screening ourselves.

Why this exists (read docs/RESEARCH.md for the full story): CelesTrak has
run full-catalog conjunction screening for free, publicly, three times a
day, since 2004, using professional-grade STK/Conjunction Analysis Tools
and real orbit-determination covariance. There is no honest case for this
project re-deriving inferior numbers with a toy propagator when the real,
trusted numbers are a public HTTP request away. This project's actual value
add is downstream of this data: turning it into accessible, explained,
prioritized guidance (see reasoning_agent.py / run_triage.py).

Data format: documented at https://celestrak.org/SOCRATES/socrates-format.php
CSV header (confirmed from that page):
    NORAD_CAT_ID_1,OBJECT_NAME_1,DSE_1,NORAD_CAT_ID_2,OBJECT_NAME_2,DSE_2,
    TCA,TCA_RANGE,TCA_RELATIVE_SPEED,MAX_PROB,DILUTION

IMPORTANT — one unverified detail, flagged rather than hidden: CelesTrak's
other GP endpoints accept a `FORMAT=CSV` query parameter, and this module
assumes `table-socrates.php` follows the same convention. This sandbox
could not confirm that directly (celestrak.org blocks automated fetches
from this environment both via robots.txt and a 403 on direct requests).
Before relying on this in production, open the URL built by
`_build_url()` in a browser once and confirm it returns the CSV described
above rather than an HTML results table — adjust `FORMAT_PARAM` below if
not.

Usage policy (see https://celestrak.org/usage-policy.php): SOCRATES Plus
updates every 10-11 hours; only download once per update. This module
enforces a minimum re-fetch interval accordingly, same pattern as
live_fetch.py for GP/TLE data.
"""
from __future__ import annotations

import csv
import io
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SOCRATES_BASE_URL = "https://celestrak.org/SOCRATES-Plus/table-socrates.php"
FORMAT_PARAM = "FORMAT=CSV"  # unverified assumption — see module docstring
DEFAULT_CACHE_PATH = Path("data/socrates_cache/latest.csv")
MIN_REFETCH_SECONDS = 10 * 60 * 60  # 10 hours — matches SOCRATES Plus's own update cadence
USER_AGENT = "orbital-collision-agent/1.0 (educational project; contact via GitHub repo)"

EXPECTED_HEADER = [
    "NORAD_CAT_ID_1", "OBJECT_NAME_1", "DSE_1",
    "NORAD_CAT_ID_2", "OBJECT_NAME_2", "DSE_2",
    "TCA", "TCA_RANGE", "TCA_RELATIVE_SPEED", "MAX_PROB", "DILUTION",
]


class SocratesFetchError(RuntimeError):
    pass


@dataclass
class SocratesConjunction:
    """One row of real SOCRATES Plus output. Every field here is CelesTrak's
    number, not ours — miss_distance_km and max_probability come from their
    STK/CAT run with real orbit-determination covariance, not our own
    assumed-covariance placeholder in probability_of_collision.py."""
    norad_id_1: str
    object_name_1: str
    days_since_epoch_1: float
    norad_id_2: str
    object_name_2: str
    days_since_epoch_2: float
    tca_utc: str
    miss_distance_km: float
    relative_speed_km_s: float
    max_probability: float
    dilution: str


def _build_url(name_filter: str = ",", order: str = "MAXPROB", max_results: int = 200) -> str:
    return f"{SOCRATES_BASE_URL}?NAME={name_filter}&ORDER={order}&MAX={max_results}&{FORMAT_PARAM}"


def _parse_csv(text: str) -> list[SocratesConjunction]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or list(reader.fieldnames) != EXPECTED_HEADER:
        raise SocratesFetchError(
            f"Unexpected SOCRATES CSV header: {reader.fieldnames!r}. "
            f"Expected: {EXPECTED_HEADER!r}. The FORMAT=CSV assumption in "
            f"this module may be wrong — see the module docstring."
        )

    results = []
    for row in reader:
        results.append(
            SocratesConjunction(
                norad_id_1=row["NORAD_CAT_ID_1"],
                object_name_1=row["OBJECT_NAME_1"],
                days_since_epoch_1=float(row["DSE_1"]),
                norad_id_2=row["NORAD_CAT_ID_2"],
                object_name_2=row["OBJECT_NAME_2"],
                days_since_epoch_2=float(row["DSE_2"]),
                tca_utc=row["TCA"],
                miss_distance_km=float(row["TCA_RANGE"]),
                relative_speed_km_s=float(row["TCA_RELATIVE_SPEED"]),
                max_probability=float(row["MAX_PROB"]) if row["MAX_PROB"] not in ("", None) else 0.0,
                dilution=row.get("DILUTION", ""),
            )
        )
    return results


def fetch_conjunctions(
    max_results: int = 200,
    order: str = "MAXPROB",
    cache_path: Path | str = DEFAULT_CACHE_PATH,
    min_refetch_seconds: int = MIN_REFETCH_SECONDS,
    force: bool = False,
) -> list[SocratesConjunction]:
    """Return real conjunction records from SOCRATES Plus, using a local
    cache so repeated runs within one SOCRATES update cycle (~10-11h)
    don't re-hit CelesTrak's servers unnecessarily (see usage policy note
    in the module docstring)."""
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    if not force and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if age < min_refetch_seconds:
            return _parse_csv(cache_path.read_text())

    url = _build_url(order=order, max_results=max_results)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode()
    except Exception as e:
        if cache_path.exists():
            return _parse_csv(cache_path.read_text())  # serve stale cache rather than fail
        raise SocratesFetchError(f"Failed to fetch SOCRATES data: {e}") from e

    records = _parse_csv(text)  # validate before caching
    cache_path.write_text(text)
    return records

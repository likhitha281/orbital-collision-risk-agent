"""
socrates_client.py
------------------
Fetches real conjunction screening results from CelesTrak's SOCRATES Plus
service.

SOCRATES Plus publishes a raw RFC 4180 CSV containing conjunction results.
We download that raw CSV, validate its documented schema, cache it locally,
and perform sorting/limiting locally.

Official format documentation:
https://celestrak.org/SOCRATES/socrates-format.php

CSV columns:
    NORAD_CAT_ID_1,OBJECT_NAME_1,DSE_1,
    NORAD_CAT_ID_2,OBJECT_NAME_2,DSE_2,
    TCA,TCA_RANGE,TCA_RELATIVE_SPEED,MAX_PROB,DILUTION

CelesTrak usage policy asks clients not to repeatedly download unchanged
data. SOCRATES Plus updates roughly three times per day, so this module
uses a 10-hour cache by default.
"""

from __future__ import annotations

import csv
import io
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path


# Raw SOCRATES Plus CSV.
#
# Do NOT use table-socrates.php?FORMAT=CSV. table-socrates.php is the
# HTML search-results interface and does not support the GP-style
# FORMAT=CSV parameter.
SOCRATES_CSV_URL = "https://celestrak.org/SOCRATES/sort-minRange.csv"

DEFAULT_CACHE_PATH = Path("data/socrates_cache/latest.csv")

# SOCRATES Plus normally updates about three times per day.
MIN_REFETCH_SECONDS = 10 * 60 * 60

USER_AGENT = (
    "orbital-collision-agent/1.0 "
    "(educational project; contact via GitHub repo)"
)

EXPECTED_HEADER = [
    "NORAD_CAT_ID_1",
    "OBJECT_NAME_1",
    "DSE_1",
    "NORAD_CAT_ID_2",
    "OBJECT_NAME_2",
    "DSE_2",
    "TCA",
    "TCA_RANGE",
    "TCA_RELATIVE_SPEED",
    "MAX_PROB",
    "DILUTION",
]


class SocratesFetchError(RuntimeError):
    """Raised when SOCRATES data cannot be fetched or validated."""


@dataclass
class SocratesConjunction:
    """One conjunction record from CelesTrak SOCRATES Plus."""

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


def _parse_csv(text: str) -> list[SocratesConjunction]:
    """
    Parse and validate CelesTrak's raw SOCRATES Plus CSV.
    """

    # Remove UTF-8 BOM if CelesTrak ever includes one.
    text = text.lstrip("\ufeff")

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise SocratesFetchError(
            "SOCRATES response did not contain a CSV header."
        )

    # Be tolerant of harmless whitespace around column names.
    actual_header = [field.strip() for field in reader.fieldnames]

    if actual_header != EXPECTED_HEADER:
        preview = text[:200].replace("\n", "\\n")

        raise SocratesFetchError(
            "Unexpected SOCRATES CSV header.\n"
            f"Received: {actual_header!r}\n"
            f"Expected: {EXPECTED_HEADER!r}\n"
            f"Response begins with: {preview!r}"
        )

    results: list[SocratesConjunction] = []

    for line_number, row in enumerate(reader, start=2):
        try:
            max_prob_raw = row.get("MAX_PROB", "")

            max_probability = (
                float(max_prob_raw)
                if max_prob_raw not in ("", None)
                else 0.0
            )

            results.append(
                SocratesConjunction(
                    norad_id_1=row["NORAD_CAT_ID_1"].strip(),
                    object_name_1=row["OBJECT_NAME_1"].strip(),
                    days_since_epoch_1=float(row["DSE_1"]),

                    norad_id_2=row["NORAD_CAT_ID_2"].strip(),
                    object_name_2=row["OBJECT_NAME_2"].strip(),
                    days_since_epoch_2=float(row["DSE_2"]),

                    tca_utc=row["TCA"].strip(),
                    miss_distance_km=float(row["TCA_RANGE"]),
                    relative_speed_km_s=float(
                        row["TCA_RELATIVE_SPEED"]
                    ),
                    max_probability=max_probability,
                    dilution=(row.get("DILUTION") or "").strip(),
                )
            )

        except (TypeError, ValueError, KeyError) as exc:
            raise SocratesFetchError(
                f"Invalid SOCRATES CSV row at line {line_number}: "
                f"{row!r}"
            ) from exc

    if not results:
        raise SocratesFetchError(
            "SOCRATES CSV was valid but contained no conjunction records."
        )

    return results


def _sort_records(
    records: list[SocratesConjunction],
    order: str,
) -> list[SocratesConjunction]:
    """
    Reproduce the useful SOCRATES search ordering locally.

    Supported values:
        MAXPROB
        MINRANGE
        TCA
        RELSPEED
        SSC
    """

    order = order.upper()

    if order == "MAXPROB":
        return sorted(
            records,
            key=lambda r: (-r.max_probability, r.tca_utc),
        )

    if order == "MINRANGE":
        return sorted(
            records,
            key=lambda r: (r.miss_distance_km, r.tca_utc),
        )

    if order == "TCA":
        return sorted(
            records,
            key=lambda r: r.tca_utc,
        )

    if order == "RELSPEED":
        return sorted(
            records,
            key=lambda r: (-r.relative_speed_km_s, r.tca_utc),
        )

    if order == "SSC":
        def norad_sort_value(value: str):
            try:
                return int(value)
            except ValueError:
                return float("inf")

        return sorted(
            records,
            key=lambda r: (
                norad_sort_value(r.norad_id_1),
                norad_sort_value(r.norad_id_2),
                r.tca_utc,
            ),
        )

    raise ValueError(
        f"Unsupported SOCRATES order {order!r}. "
        "Expected MAXPROB, MINRANGE, TCA, RELSPEED, or SSC."
    )


def _download_csv() -> str:
    """
    Download the latest raw SOCRATES Plus CSV.
    """

    request = urllib.request.Request(
        SOCRATES_CSV_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.1",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()

    except Exception as exc:
        raise SocratesFetchError(
            f"Failed to fetch SOCRATES data from "
            f"{SOCRATES_CSV_URL}: {exc}"
        ) from exc

    try:
        return raw.decode("utf-8-sig")

    except UnicodeDecodeError as exc:
        raise SocratesFetchError(
            "SOCRATES response was not valid UTF-8 CSV."
        ) from exc


def fetch_conjunctions(
    max_results: int = 200,
    order: str = "MAXPROB",
    cache_path: Path | str = DEFAULT_CACHE_PATH,
    min_refetch_seconds: int = MIN_REFETCH_SECONDS,
    force: bool = False,
) -> list[SocratesConjunction]:
    """
    Return real conjunction records from SOCRATES Plus.

    The complete raw CSV is cached locally. Sorting and limiting are
    performed after parsing so we do not need to repeatedly query
    CelesTrak for different result orderings.
    """

    if max_results <= 0:
        return []

    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    text: str | None = None

    # ------------------------------------------------------------
    # 1. Use fresh cache when available.
    # ------------------------------------------------------------

    if not force and cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime

        if age < min_refetch_seconds:
            try:
                text = cache_path.read_text(
                    encoding="utf-8-sig"
                )
                records = _parse_csv(text)

                return _sort_records(
                    records,
                    order,
                )[:max_results]

            except (OSError, SocratesFetchError):
                # Bad cache: ignore it and attempt a fresh download.
                pass

    # ------------------------------------------------------------
    # 2. Fetch latest CSV.
    # ------------------------------------------------------------

    try:
        text = _download_csv()

        # Validate BEFORE replacing a good cache.
        records = _parse_csv(text)

    except SocratesFetchError as fetch_error:

        # --------------------------------------------------------
        # 3. Network/CelesTrak failure: use stale cache if possible.
        # --------------------------------------------------------

        if cache_path.exists():
            try:
                stale_text = cache_path.read_text(
                    encoding="utf-8-sig"
                )

                stale_records = _parse_csv(stale_text)

                return _sort_records(
                    stale_records,
                    order,
                )[:max_results]

            except (OSError, SocratesFetchError):
                pass

        raise fetch_error

    # ------------------------------------------------------------
    # 4. Cache only validated data.
    # ------------------------------------------------------------

    try:
        cache_path.write_text(
            text,
            encoding="utf-8",
        )
    except OSError:
        # A cache write failure should not throw away valid live data.
        pass

    # ------------------------------------------------------------
    # 5. Sort and return requested number of records.
    # ------------------------------------------------------------

    return _sort_records(
        records,
        order,
    )[:max_results]
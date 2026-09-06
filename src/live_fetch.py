"""
live_fetch.py
--------------
Tool #0 in the "real-time" pipeline: pulls current TLE data from Celestrak
and caches it on disk.

Celestrak's own documentation says their GP/TLE data is refreshed roughly
every 2 hours, and explicitly asks users not to poll more often than that
(their FAQ describes rate-limiting/blocking users who re-download far more
often than the data actually changes). So "real-time" here means "always
within one refresh cycle of current," not sub-second streaming — this
module enforces a minimum re-fetch interval (default 2 hours) via a local
cache, both to be a good citizen of a free public data source and because
fetching more often literally cannot get you fresher data.

Usage:
    from src.live_fetch import fetch_live_catalog
    path = fetch_live_catalog(group="stations")   # -> path to a fresh .tle file

Network note: this module makes outbound HTTP requests and will not work in
network-restricted sandboxes. It's meant to be run in your own environment,
a scheduled CI job, or a server with normal internet access.
"""
from __future__ import annotations

import time
import urllib.request
from pathlib import Path

CELESTRAK_URL_TEMPLATE = "https://celestrak.org/NORAD/elements/gp.php?GROUP={group}&FORMAT=tle"
DEFAULT_CACHE_DIR = Path("data/live_cache")
MIN_REFETCH_SECONDS = 2 * 60 * 60  # 2 hours — matches Celestrak's own refresh cadence
USER_AGENT = "orbital-collision-agent/1.0 (educational capstone project; contact via GitHub repo)"


class LiveFetchError(RuntimeError):
    pass


def _cache_path(group: str, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{group}.tle"


def fetch_live_catalog(
    group: str = "stations",
    cache_dir: Path | str = DEFAULT_CACHE_DIR,
    min_refetch_seconds: int = MIN_REFETCH_SECONDS,
    force: bool = False,
) -> Path:
    """Return a path to a locally-cached TLE file for `group`, fetching a
    fresh copy from Celestrak only if the cache is older than
    `min_refetch_seconds` (or missing, or `force=True`).

    `group` is any valid Celestrak GROUP query value, e.g. "stations",
    "active", "starlink", "gps-ops", "debris". See
    https://celestrak.org/NORAD/elements/ for the full list.
    """
    cache_dir = Path(cache_dir)
    path = _cache_path(group, cache_dir)

    if not force and path.exists():
        age_seconds = time.time() - path.stat().st_mtime
        if age_seconds < min_refetch_seconds:
            return path  # cache is still fresh enough; don't hit the network

    url = CELESTRAK_URL_TEMPLATE.format(group=group)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode()
    except Exception as e:
        if path.exists():
            # Fetch failed (network hiccup, rate limit, outage) — serve the
            # stale cache rather than hard-failing the whole pipeline.
            return path
        raise LiveFetchError(f"Failed to fetch live TLE data for group={group!r}: {e}") from e

    if not data.strip() or "1 " not in data:
        raise LiveFetchError(f"Celestrak returned unexpected content for group={group!r}")

    path.write_text(data)
    return path

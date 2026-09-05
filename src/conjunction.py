"""
conjunction.py
--------------
Tool #2 in the agent's toolchain: propagates every pair of objects in a
catalog over a lookahead window using SGP4 (via Skyfield) and screens for
close approaches ("conjunctions").

This is intentionally a simple, coarse screener suitable for a baseline:
it samples relative distance on a fixed time grid rather than doing
adaptive root-finding on the minimum. That is a known limitation, called
out explicitly in the project's Limitations section.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
from skyfield.api import load

from .tle_loader import CatalogObject


@dataclass
class ConjunctionEvent:
    object_a: str
    object_b: str
    norad_a: str
    norad_b: str
    time_utc: str
    miss_distance_km: float
    relative_speed_km_s: float
    involves_synthetic: bool


def screen_conjunctions(
    objects: list[CatalogObject],
    lookahead_seconds: int = 6000,
    step_seconds: int = 1,
    flag_threshold_km: float = 25.0,
) -> list[ConjunctionEvent]:
    """Screen every pair of objects for close approaches within
    `lookahead_seconds` of the (shared) TLE epoch, sampled every
    `step_seconds`. Returns events whose minimum sampled distance is below
    `flag_threshold_km`, sorted by miss distance ascending (highest risk
    first).
    """
    ts = load.timescale()
    events: list[ConjunctionEvent] = []

    for a, b in combinations(objects, 2):
        # Use object A's epoch as the reference start time for the window.
        t0 = a.satellite.epoch
        offsets = np.arange(0, lookahead_seconds, step_seconds)
        times = ts.tt_jd(t0.tt + offsets / 86400.0)

        diffs = (a.satellite - b.satellite).at(times)
        dist_km = diffs.distance().km

        idx = int(np.argmin(dist_km))
        min_dist = float(dist_km[idx])

        if min_dist <= flag_threshold_km:
            # Total relative speed (not just the radial component, which is ~0
            # by definition at the point of closest approach) from the
            # instantaneous relative velocity vector.
            closest_diff = (a.satellite - b.satellite).at(times[idx])
            rel_speed = float(np.linalg.norm(closest_diff.velocity.km_per_s))

            events.append(
                ConjunctionEvent(
                    object_a=a.name,
                    object_b=b.name,
                    norad_a=a.norad_id,
                    norad_b=b.norad_id,
                    time_utc=times[idx].utc_iso(),
                    miss_distance_km=round(min_dist, 3),
                    relative_speed_km_s=round(rel_speed, 4),
                    involves_synthetic=a.is_synthetic or b.is_synthetic,
                )
            )

    events.sort(key=lambda e: e.miss_distance_km)
    return events

"""
trends.py
----------
Detects how collision risk for a specific object pair + TCA has changed
across repeated SOCRATES observations. This is the piece that turns the
agent from "describes one snapshot" into "notices Pc increased 40x since
the last check" — the single biggest gap in the earlier version.
"""
from __future__ import annotations

from dataclasses import dataclass

from .observation_store import Observation

ESCALATION_RATIO = 2.0   # Pc at least doubled since the oldest observation -> escalating
DECREASE_RATIO = 0.5     # Pc at most halved -> decreasing


@dataclass(frozen=True)
class RiskTrend:
    direction: str  # "escalating" | "decreasing" | "stable" | "insufficient_data"
    pc_change_ratio: float | None
    miss_distance_change_km: float | None
    observations: int


def calculate_trend(history: list[Observation]) -> RiskTrend:
    """`history` must be ordered oldest-first (as ObservationRepository.history_for
    returns it). Compares the oldest and newest observation on record — not
    just the two most recent — so a single noisy update doesn't flip the
    verdict."""
    if len(history) < 2:
        return RiskTrend(
            direction="insufficient_data",
            pc_change_ratio=None,
            miss_distance_change_km=None,
            observations=len(history),
        )

    oldest, newest = history[0], history[-1]

    ratio = (
        newest.probability_of_collision / oldest.probability_of_collision
        if oldest.probability_of_collision > 0
        else None
    )
    miss_change = newest.miss_distance_km - oldest.miss_distance_km

    if ratio is not None and ratio >= ESCALATION_RATIO:
        direction = "escalating"
    elif ratio is not None and ratio <= DECREASE_RATIO:
        direction = "decreasing"
    else:
        direction = "stable"

    return RiskTrend(
        direction=direction,
        pc_change_ratio=round(ratio, 2) if ratio is not None else None,
        miss_distance_change_km=round(miss_change, 3),
        observations=len(history),
    )

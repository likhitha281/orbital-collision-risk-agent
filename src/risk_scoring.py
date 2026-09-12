"""
risk_scoring.py
-----------------
Deterministic operational priority scoring — kept explicitly separate from
the LLM layer (src/analyst.py). The LLM never computes or adjusts this
score; it only explains it.

This directly addresses a real, fair critique of an earlier version: a
MEDIUM tier sitting next to a near-zero probability of collision is
indefensible unless the tiering logic is transparent about what it's
actually measuring. This module scores three named factors and shows its
work via `reasons`, instead of collapsing straight to a label.

The three factors:
  - pc_score: how severe is the collision probability itself (log-scaled,
    since Pc spans many orders of magnitude)
  - urgency_score: how soon is the closest approach
  - freshness_score: how old is the underlying tracking data (staler data
    should pull priority down, not up — an old, uncertain prediction isn't
    more urgent, it's less trustworthy)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RiskAssessment:
    priority_score: float  # 0-100
    priority_tier: str     # HIGH / MEDIUM / LOW
    pc_score: float
    urgency_score: float
    freshness_score: float
    reasons: tuple[str, ...]


def _pc_score(pc: float) -> float:
    """Log-scaled so the huge dynamic range of Pc (1e-2 down to 1e-22)
    maps to a sane 0-100 severity. 1e-2 or worse -> 100; 1e-8 or better -> ~0."""
    if pc <= 0:
        return 0.0
    score = (math.log10(pc) + 8) / 6 * 100
    return max(0.0, min(100.0, score))


def _urgency_score(hours_to_tca: float) -> float:
    if hours_to_tca <= 6:
        return 100.0
    if hours_to_tca >= 72:
        return 0.0
    return 100.0 * (72 - hours_to_tca) / (72 - 6)


def _freshness_score(max_dse_days: float) -> float:
    """Higher score = fresher data. Deliberately does NOT feed into
    urgency — stale data makes a prediction less trustworthy, not more
    actionable, so it should pull priority toward 'needs a re-screen'
    rather than toward 'act now'."""
    if max_dse_days <= 1:
        return 100.0
    if max_dse_days >= 7:
        return 0.0
    return 100.0 * (7 - max_dse_days) / (7 - 1)


def _tier(score: float, pc_score: float) -> str:
    """Pc severity gates the ceiling: urgency and freshness modulate
    priority WITHIN a tier the collision probability already justifies,
    they can't manufacture concern out of a negligible Pc. Without this
    gate, a near-zero Pc paired with an imminent, fresh-data TCA could
    still score MEDIUM on urgency+freshness alone — which is exactly the
    "Pc=7.8e-22 but MEDIUM" problem this scoring model exists to prevent."""
    if pc_score < 5:
        return "LOW"
    if pc_score < 20:
        return "LOW" if score < 50 else "MEDIUM"
    if score >= 65:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def assess(
    probability_of_collision: float,
    tca_utc: datetime,
    max_days_since_epoch: float,
    now: datetime | None = None,
    weights: tuple[float, float, float] = (0.6, 0.25, 0.15),
) -> RiskAssessment:
    """weights = (pc, urgency, freshness); should sum to 1.0. Pc is
    weighted most heavily on purpose — urgency and freshness modulate
    priority, they don't override what the actual collision probability
    is telling you."""
    now = now or datetime.now(timezone.utc)
    hours_to_tca = max((tca_utc - now).total_seconds() / 3600.0, 0.0)

    pc = _pc_score(probability_of_collision)
    urgency = _urgency_score(hours_to_tca)
    freshness = _freshness_score(max_days_since_epoch)

    w_pc, w_urgency, w_fresh = weights
    score = w_pc * pc + w_urgency * urgency + w_fresh * freshness
    tier = _tier(score, pc)

    reasons = []
    if pc >= 65:
        reasons.append(f"Collision probability ({probability_of_collision:.2e}) is in the high-concern range")
    elif pc <= 15:
        reasons.append(f"Collision probability ({probability_of_collision:.2e}) is low")
    if urgency >= 65:
        reasons.append(f"Closest approach is soon ({hours_to_tca:.1f}h away)")
    if freshness <= 35:
        reasons.append(f"Underlying tracking data is {max_days_since_epoch:.1f} days old — treat as less certain")
    if not reasons:
        reasons.append("No individual factor is extreme; priority reflects a moderate combination")

    return RiskAssessment(
        priority_score=round(score, 1),
        priority_tier=tier,
        pc_score=round(pc, 1),
        urgency_score=round(urgency, 1),
        freshness_score=round(freshness, 1),
        reasons=tuple(reasons),
    )

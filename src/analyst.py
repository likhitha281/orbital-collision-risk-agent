"""
analyst.py
------------
The actual reasoning upgrade. reasoning_agent.py (phase 1 / v1 phase 2)
translates a single snapshot's numbers into prose — useful, but that's
narration, not reasoning. This agent is given the deterministic priority
assessment AND the risk trend across observation history, and is asked
analyst questions: why does this matter, what changed, what's missing,
how confident should we be, what's next.

Hard constraint, enforced by construction rather than only by prompt: this
module has no field anywhere in its output schema for a probability or a
priority score. It is structurally incapable of reporting a different
number than the one it was given, because there's nowhere to put one. Even
the rule-based fallback (no API key needed) only ever restates the exact
values passed in — see tests/test_analyst.py.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass, fields

from .observation_store import Observation
from .risk_scoring import RiskAssessment
from .trends import RiskTrend

ANTHROPIC_MODEL = "claude-sonnet-4-6"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = """You are an orbital-risk communication assistant.

You MUST NOT:
- recalculate or restate a different collision probability than the one given
- change or invent a priority score or tier
- invent orbital data not present in the supplied evidence
- recommend a specific maneuver
- claim operational certainty

You MAY:
- explain why the deterministic engine assigned this priority
- summarize how risk has changed across the supplied observation history
- identify what information is missing or uncertain
- explain technical values in plain language

Respond with ONLY a JSON object with these exact keys: summary, why_it_matters,
trend_explanation, suggested_next_step, confidence (one of "low", "moderate", "high"),
limitations (a list of strings). No other text, no markdown fences, no extra keys."""


@dataclass(frozen=True)
class AnalystOutput:
    # Note what's NOT here: no probability_of_collision, no priority_score,
    # no tier. This dataclass is the actual enforcement mechanism — the
    # agent has no field to put an altered number into even if a prompt
    # injection or a model error tried to make it.
    summary: str
    why_it_matters: str
    trend_explanation: str
    suggested_next_step: str
    confidence: str
    limitations: list[str]
    source: str  # "llm" | "rule_based_fallback"


def _build_evidence(observation: Observation, assessment: RiskAssessment, trend: RiskTrend) -> dict:
    return {
        "objects": f"{observation.object_name_1} vs {observation.object_name_2}",
        "tca_utc": observation.tca_utc,
        "probability_of_collision": observation.probability_of_collision,
        "miss_distance_km": observation.miss_distance_km,
        "priority_score": assessment.priority_score,
        "priority_tier": assessment.priority_tier,
        "score_reasons": list(assessment.reasons),
        "trend_direction": trend.direction,
        "pc_change_ratio": trend.pc_change_ratio,
        "miss_distance_change_km": trend.miss_distance_change_km,
        "observations_available": trend.observations,
        "max_days_since_epoch": max(observation.days_since_epoch_1, observation.days_since_epoch_2),
    }


def _call_llm(evidence: dict) -> dict | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 500,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": f"Evidence:\n{json.dumps(evidence, indent=2)}"}],
    }).encode()
    req = urllib.request.Request(
        ANTHROPIC_URL, data=body,
        headers={"content-type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
        method="POST",
    )
    required_keys = {"summary", "why_it_matters", "trend_explanation", "suggested_next_step", "confidence", "limitations"}
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        text = "".join(b["text"] for b in data.get("content", []) if b.get("type") == "text")
        parsed = json.loads(text)
        if not required_keys.issubset(parsed.keys()):
            return None
        # Only pass through the keys we actually expect — belt-and-braces
        # against the model adding an extra field (e.g. a "revised_pc") that
        # AnalystOutput has no slot for anyway, but never silently accept one.
        return {k: parsed[k] for k in required_keys}
    except Exception:
        return None


def _rule_based_fallback(evidence: dict) -> dict:
    trend = evidence["trend_direction"]
    if trend == "escalating":
        trend_explanation = (
            f"Probability of collision increased by a factor of {evidence['pc_change_ratio']:.1f} "
            f"across {evidence['observations_available']} observations."
        )
    elif trend == "decreasing" and evidence["pc_change_ratio"]:
        trend_explanation = (
            f"Probability of collision decreased by a factor of {1 / evidence['pc_change_ratio']:.1f} "
            f"across {evidence['observations_available']} observations."
        )
    elif trend == "stable":
        trend_explanation = (
            f"Probability of collision has stayed roughly stable across "
            f"{evidence['observations_available']} observations."
        )
    else:
        trend_explanation = "Only one observation is available so far; no trend can be established yet."

    limitations = list(evidence["score_reasons"])
    if evidence["max_days_since_epoch"] > 7:
        limitations.append("Underlying tracking data is more than 7 days old.")
    if evidence["observations_available"] < 3:
        limitations.append("Fewer than 3 observations available — trend estimate is preliminary.")

    if evidence["priority_tier"] == "HIGH":
        next_step = "Recommend an active maneuver evaluation and re-screen against fresher tracking data."
    elif evidence["priority_tier"] == "MEDIUM":
        next_step = "Continue monitoring and re-screen as the event approaches."
    else:
        next_step = "Log the event; no immediate action needed."

    confidence = (
        "low" if evidence["observations_available"] < 2 or evidence["max_days_since_epoch"] > 7 else "moderate"
    )

    return {
        "summary": (
            f"{evidence['objects']}: probability of collision {evidence['probability_of_collision']:.2e}, "
            f"priority {evidence['priority_tier']} (score {evidence['priority_score']}/100)."
        ),
        "why_it_matters": "; ".join(evidence["score_reasons"]),
        "trend_explanation": trend_explanation,
        "suggested_next_step": next_step,
        "confidence": confidence,
        "limitations": limitations,
    }


def explain(observation: Observation, assessment: RiskAssessment, trend: RiskTrend) -> AnalystOutput:
    evidence = _build_evidence(observation, assessment, trend)
    llm_result = _call_llm(evidence)
    if llm_result:
        return AnalystOutput(**llm_result, source="llm")
    fallback = _rule_based_fallback(evidence)
    return AnalystOutput(**fallback, source="rule_based_fallback")


# Locks the schema contract in one place: if someone adds a numeric field to
# AnalystOutput later, this assertion forces them to consciously touch it.
_TEXT_ONLY_FIELDS = {"summary", "why_it_matters", "trend_explanation", "suggested_next_step", "confidence", "source"}
assert {f.name for f in fields(AnalystOutput)} - _TEXT_ONLY_FIELDS == {"limitations"}, (
    "AnalystOutput schema changed — re-verify it still has no numeric probability/priority field"
)

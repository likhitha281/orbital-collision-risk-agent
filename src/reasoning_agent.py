"""
reasoning_agent.py
--------------------
Tool #4 / orchestrator: turns a list of ConjunctionEvents plus retrieved
knowledge-base notes into a human-readable risk report.

Two modes:
  * LLM mode (default if ANTHROPIC_API_KEY is set): calls the Anthropic
    Messages API to draft the narrative recommendation, grounded in the
    retrieved notes and the raw numbers (the numbers themselves always
    come from the deterministic conjunction screener, never from the LLM).
  * Rule-based fallback (no API key required): produces a structured
    report using fixed templates keyed off the risk tiers, so the whole
    pipeline stays runnable and reproducible with zero external
    dependencies or credentials, per the assignment's requirements.
"""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import asdict

from .conjunction import ConjunctionEvent
from .knowledge_base import KnowledgeBase

ANTHROPIC_MODEL = "claude-sonnet-4-6"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def _risk_tier(miss_km: float) -> str:
    if miss_km < 1.0:
        return "HIGH"
    if miss_km < 5.0:
        return "MEDIUM"
    return "LOW"


def _rule_based_recommendation(event: ConjunctionEvent, tier: str) -> str:
    if tier == "HIGH":
        return (
            f"Miss distance of {event.miss_distance_km} km is inside the high-concern "
            "band. Recommend an active maneuver evaluation and re-screening against "
            "the freshest available tracking data before the predicted close-approach "
            "time."
        )
    if tier == "MEDIUM":
        return (
            f"Miss distance of {event.miss_distance_km} km warrants close monitoring "
            "and a maneuver plan on standby, with a re-screen as the event approaches."
        )
    return (
        f"Miss distance of {event.miss_distance_km} km is outside the typical action "
        "threshold. Log the event and continue routine monitoring."
    )


def _call_anthropic(prompt: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    body = json.dumps(
        {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=body,
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        return "\n".join(text_blocks).strip() or None
    except Exception:
        # Any network/auth failure silently falls back to the rule-based path
        # so the baseline never hard-fails just because the LLM call failed.
        return None


def generate_event_report(event: ConjunctionEvent, kb: KnowledgeBase) -> dict:
    tier = _risk_tier(event.miss_distance_km)
    notes = kb.retrieve(
        f"conjunction risk tier {tier} miss distance {event.miss_distance_km} km maneuver"
    )
    notes_text = "\n".join(f"- {n.text}" for n in notes)

    prompt = (
        "You are assisting a space-traffic-management analyst. Given this "
        "conjunction screening result and background notes, write a 3-5 sentence "
        "risk assessment and a concrete recommended next action. Be concrete and "
        "operational, not generic.\n\n"
        f"Event: {json.dumps(asdict(event))}\n"
        f"Risk tier (computed deterministically, do not change it): {tier}\n\n"
        f"Background notes:\n{notes_text}\n"
    )

    llm_text = _call_anthropic(prompt)
    recommendation = llm_text or _rule_based_recommendation(event, tier)

    return {
        "event": asdict(event),
        "risk_tier": tier,
        "grounding_notes": [n.id for n in notes],
        "recommendation": recommendation,
        "recommendation_source": "llm" if llm_text else "rule_based_fallback",
    }

"""
report.py
---------
Formats the agent's per-event assessments into a Markdown report and a
structured JSON summary (the JSON is what the dashboard in docs/ reads).

Provenance-aware: assessments coming from the SGP4 baseline
(run_baseline.py) carry pc_provenance="assumed_covariance" (our own toy Pc,
see probability_of_collision.py); assessments coming from the real-data
triage layer (run_triage.py) carry pc_provenance="socrates_real" (CelesTrak
SOCRATES Plus's actual Pc, computed by STK/CAT with real orbit-determination
covariance). The report text and caveats differ accordingly — an assumed
covariance number should read differently from a real one.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

PC_CAVEATS = {
    "assumed_covariance": (
        "> **Note on Pc**: these probability-of-collision figures use an "
        "*assumed* generic position-uncertainty covariance (TLEs do not include "
        "real covariance data), so treat Pc as illustrative of the method, not "
        "an operational-grade number. Risk tiers are driven by miss distance "
        "for that reason. See docs/RESEARCH.md."
    ),
    "socrates_real": (
        "> **Note on Pc**: these probability-of-collision figures are CelesTrak "
        "SOCRATES Plus's own published numbers, computed with STK/Conjunction "
        "Analysis Tools using real orbit-determination covariance — not this "
        "project's own estimate. Risk tiers below are based on that real "
        "probability. See docs/RESEARCH.md."
    ),
}


def _pc_provenance(assessments: list[dict]) -> str:
    if not assessments:
        return "assumed_covariance"
    return assessments[0]["event"].get("pc_provenance", "assumed_covariance")


def render_report(source_label: str, assessments: list[dict]) -> str:
    lines = []
    lines.append("# Orbital Collision-Risk Report")
    lines.append("")
    lines.append(f"- Data source: `{source_label}`")
    lines.append(f"- Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    lines.append(f"- Conjunctions flagged: {len(assessments)}")
    lines.append("")

    if not assessments:
        lines.append("No conjunctions found below the screening threshold.")
        return "\n".join(lines)

    lines.append(PC_CAVEATS[_pc_provenance(assessments)])
    lines.append("")

    for i, a in enumerate(assessments, start=1):
        e = a["event"]
        synthetic_note = " _(involves a synthetic test object)_" if e["involves_synthetic"] else ""
        provenance_label = "real, CelesTrak SOCRATES Plus" if e.get("pc_provenance") == "socrates_real" else "assumed covariance"
        lines.append(f"## {i}. {e['object_a']} vs {e['object_b']}{synthetic_note}")
        lines.append("")
        lines.append(f"- NORAD IDs: {e['norad_a']} / {e['norad_b']}")
        lines.append(f"- Time of closest approach (UTC): {e['time_utc']}")
        lines.append(f"- Miss distance: **{e['miss_distance_km']} km**")
        lines.append(f"- Relative speed at closest approach: {e['relative_speed_km_s']} km/s")
        lines.append(
            f"- Probability of collision ({provenance_label}): "
            f"**{e['probability_of_collision']:.3e}**"
        )
        lines.append(f"- Risk tier: **{a['risk_tier']}**")
        if e.get("stale_tle"):
            lines.append("- ⚠️ **Tracking data >7 days old** — treat as indicative, re-screen before acting")
        lines.append(f"- Grounded on notes: {', '.join(a['grounding_notes'])}")
        lines.append(f"- Recommendation ({a['recommendation_source']}):")
        lines.append(f"  > {a['recommendation']}")
        lines.append("")

    return "\n".join(lines)


def render_json(source_label: str, assessments: list[dict]) -> str:
    """Structured summary of the same run, for machine consumption (the
    static dashboard in docs/ fetches this directly)."""
    payload = {
        "source_label": source_label,
        "pc_provenance": _pc_provenance(assessments),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "conjunctions_flagged": len(assessments),
        "events": [
            {
                "object_a": a["event"]["object_a"],
                "object_b": a["event"]["object_b"],
                "norad_a": a["event"]["norad_a"],
                "norad_b": a["event"]["norad_b"],
                "time_utc": a["event"]["time_utc"],
                "miss_distance_km": a["event"]["miss_distance_km"],
                "relative_speed_km_s": a["event"]["relative_speed_km_s"],
                "involves_synthetic": a["event"]["involves_synthetic"],
                "probability_of_collision": a["event"]["probability_of_collision"],
                "pc_provenance": a["event"].get("pc_provenance", "assumed_covariance"),
                "risk_tier": a["risk_tier"],
                "grounding_notes": a["grounding_notes"],
                "recommendation": a["recommendation"],
                "recommendation_source": a["recommendation_source"],
            }
            for a in assessments
        ],
    }
    return json.dumps(payload, indent=2)

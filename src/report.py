"""
report.py
---------
Formats the agent's per-event assessments into a Markdown report and a
structured JSON summary (the JSON is what the dashboard in docs/ reads).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone


def render_report(catalog_path: str, assessments: list[dict]) -> str:
    lines = []
    lines.append("# Orbital Collision-Risk Report")
    lines.append("")
    lines.append(f"- Catalog file: `{catalog_path}`")
    lines.append(f"- Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    lines.append(f"- Conjunctions flagged: {len(assessments)}")
    lines.append("")

    if not assessments:
        lines.append("No conjunctions found below the screening threshold.")
        return "\n".join(lines)

    lines.append(
        "> **Note on Pc**: the probability-of-collision figures below use an "
        "*assumed* generic position-uncertainty covariance (TLEs do not include "
        "real covariance data), so treat Pc as illustrative of the method, not "
        "an operational-grade number. Risk tiers are driven by miss distance "
        "for that reason. See the main README's Research & References and "
        "Limitations sections."
    )
    lines.append("")

    for i, a in enumerate(assessments, start=1):
        e = a["event"]
        synthetic_note = " _(involves a synthetic test object)_" if e["involves_synthetic"] else ""
        lines.append(f"## {i}. {e['object_a']} vs {e['object_b']}{synthetic_note}")
        lines.append("")
        lines.append(f"- NORAD IDs: {e['norad_a']} / {e['norad_b']}")
        lines.append(f"- Time of closest approach (UTC): {e['time_utc']}")
        lines.append(f"- Miss distance: **{e['miss_distance_km']} km**")
        lines.append(f"- Relative speed at closest approach: {e['relative_speed_km_s']} km/s")
        lines.append(
            f"- Probability of collision (2D-Pc, Foster & Estes 1992; "
            f"*assumed* covariance, see [Research & References](../README.md#research--references)): "
            f"**{e['probability_of_collision']:.3e}**"
        )
        lines.append(f"- Risk tier: **{a['risk_tier']}** (based on miss distance, not Pc — see note below)")
        lines.append(f"- Grounded on notes: {', '.join(a['grounding_notes'])}")
        lines.append(f"- Recommendation ({a['recommendation_source']}):")
        lines.append(f"  > {a['recommendation']}")
        lines.append("")

    return "\n".join(lines)


def render_json(catalog_path: str, assessments: list[dict]) -> str:
    """Structured summary of the same run, for machine consumption (the
    static dashboard in docs/ fetches this directly)."""
    payload = {
        "catalog_path": catalog_path,
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
                "risk_tier": a["risk_tier"],
                "grounding_notes": a["grounding_notes"],
                "recommendation": a["recommendation"],
                "recommendation_source": a["recommendation_source"],
            }
            for a in assessments
        ],
    }
    return json.dumps(payload, indent=2)

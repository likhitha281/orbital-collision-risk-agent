"""
report.py
---------
Formats the agent's per-event assessments into a single Markdown report.
"""
from __future__ import annotations

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

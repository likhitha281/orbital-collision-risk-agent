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

    for i, a in enumerate(assessments, start=1):
        e = a["event"]
        synthetic_note = " _(involves a synthetic test object)_" if e["involves_synthetic"] else ""
        lines.append(f"## {i}. {e['object_a']} vs {e['object_b']}{synthetic_note}")
        lines.append("")
        lines.append(f"- NORAD IDs: {e['norad_a']} / {e['norad_b']}")
        lines.append(f"- Time of closest approach (UTC): {e['time_utc']}")
        lines.append(f"- Miss distance: **{e['miss_distance_km']} km**")
        lines.append(f"- Relative speed at closest approach: {e['relative_speed_km_s']} km/s")
        lines.append(f"- Risk tier: **{a['risk_tier']}**")
        lines.append(f"- Grounded on notes: {', '.join(a['grounding_notes'])}")
        lines.append(f"- Recommendation ({a['recommendation_source']}):")
        lines.append(f"  > {a['recommendation']}")
        lines.append("")

    return "\n".join(lines)

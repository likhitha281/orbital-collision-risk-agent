#!/usr/bin/env python3
"""
run_triage.py
--------------
Phase 2, v2: real-data triage with actual reasoning, not narration.

Pipeline:
  1. socrates_client.fetch_conjunctions -> real, published conjunction data
  2. triage.prioritize                  -> filter/sort by real Pc
  3. observation_store.save_many        -> persist this run's observations.
                                            This is what makes reasoning
                                            possible on future runs: without
                                            history, there's nothing to
                                            reason about except one snapshot.
  4. risk_scoring.assess                -> deterministic priority score from
                                            Pc severity + urgency (time to
                                            TCA) + tracking freshness. Never
                                            computed or adjusted by the LLM.
  5. observation_store.history_for      -> this pair's full observation
                                            history (accumulates run over run
                                            as the scheduled workflow repeats)
  6. trends.calculate_trend             -> has risk gotten better or worse
                                            since the oldest observation on
                                            record?
  7. analyst.explain                    -> explains WHY this matters and
                                            WHAT changed, grounded only in
                                            the evidence above. Structurally
                                            unable to alter the Pc or the
                                            priority score — see src/analyst.py.

The JSON output keeps `conjunctions_flagged` and `events[].probability_of_collision`
at the top level for backward compatibility with action.yml's output parsing;
each event is otherwise a richer object than v1 (priority score breakdown,
trend, and the analyst's structured explanation).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from src.analyst import explain
from src.observation_store import Observation, ObservationRepository, pair_key
from src.risk_scoring import assess
from src.socrates_client import SocratesFetchError, fetch_conjunctions
from src.trends import calculate_trend
from src.triage import prioritize


def _parse_tca(tca_str: str) -> datetime:
    dt = datetime.fromisoformat(tca_str.replace("Z", ""))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def main() -> int:
    parser = argparse.ArgumentParser(description="Real-data conjunction triage with trend-aware reasoning (phase 2)")
    parser.add_argument("--max-results", type=int, default=50, help="Max conjunctions to fetch from SOCRATES Plus")
    parser.add_argument("--min-probability", type=float, default=0.0, help="Drop events below this probability of collision")
    parser.add_argument("--limit", type=int, default=20, help="Max events to run the full reasoning pass on")
    parser.add_argument("--output", default="triage_report.md", help="Path to write the Markdown report to")
    parser.add_argument("--db-path", default="data/orbital_history.db", help="SQLite history database path")
    args = parser.parse_args()

    print(f"[1/5] Fetching up to {args.max_results} real conjunctions from CelesTrak SOCRATES Plus ...")
    try:
        records = fetch_conjunctions(max_results=args.max_results, order="MAXPROB")
    except SocratesFetchError as e:
        print(f"      Fetch failed: {e}")
        print("      (Expected in network-restricted environments — see README.)")
        return 1
    print(f"      Retrieved {len(records)} record(s)")

    prioritized = prioritize(records, min_probability=args.min_probability, limit=args.limit)
    print(f"[2/5] Triaging {len(prioritized)} event(s) after filtering/limiting")

    repo = ObservationRepository(args.db_path)
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    inserted = repo.save_many(prioritized, observed_at=observed_at)
    print(f"[3/5] Persisted {inserted} new observation(s) to {args.db_path} (history accumulates run over run)")

    now = datetime.now(timezone.utc)
    results = []
    for r in prioritized:
        id1, id2 = pair_key(r.norad_id_1, r.norad_id_2)
        history = repo.history_for(id1, id2, r.tca_utc)

        current = history[-1] if history else Observation(
            norad_id_1=id1, norad_id_2=id2,
            object_name_1=r.object_name_1, object_name_2=r.object_name_2,
            tca_utc=r.tca_utc, observed_at=observed_at,
            miss_distance_km=r.miss_distance_km, relative_speed_km_s=r.relative_speed_km_s,
            probability_of_collision=r.max_probability,
            days_since_epoch_1=r.days_since_epoch_1, days_since_epoch_2=r.days_since_epoch_2,
        )

        trend = calculate_trend(history)
        assessment = assess(
            probability_of_collision=current.probability_of_collision,
            tca_utc=_parse_tca(current.tca_utc),
            max_days_since_epoch=max(current.days_since_epoch_1, current.days_since_epoch_2),
            now=now,
        )
        analysis = explain(current, assessment, trend)

        results.append({
            "object_a": current.object_name_1,
            "object_b": current.object_name_2,
            "norad_a": current.norad_id_1,
            "norad_b": current.norad_id_2,
            "time_utc": current.tca_utc,
            "miss_distance_km": current.miss_distance_km,
            "relative_speed_km_s": current.relative_speed_km_s,
            "probability_of_collision": current.probability_of_collision,
            "pc_provenance": "socrates_real",
            "priority_score": assessment.priority_score,
            "priority_tier": assessment.priority_tier,
            "score_breakdown": {
                "pc_score": assessment.pc_score,
                "urgency_score": assessment.urgency_score,
                "freshness_score": assessment.freshness_score,
            },
            "score_reasons": list(assessment.reasons),
            "trend": {
                "direction": trend.direction,
                "pc_change_ratio": trend.pc_change_ratio,
                "miss_distance_change_km": trend.miss_distance_change_km,
                "observations": trend.observations,
            },
            "analysis": {
                "summary": analysis.summary,
                "why_it_matters": analysis.why_it_matters,
                "trend_explanation": analysis.trend_explanation,
                "suggested_next_step": analysis.suggested_next_step,
                "confidence": analysis.confidence,
                "limitations": analysis.limitations,
                "source": analysis.source,
            },
        })

    results.sort(key=lambda e: e["priority_score"], reverse=True)
    print(f"[4/5] Generated {len(results)} evidence-grounded assessment(s)")

    print(f"[5/5] Writing report to {args.output} ...")
    md_lines = [
        "# Orbital Collision-Risk Triage Report", "",
        "- Data source: CelesTrak SOCRATES Plus (real conjunction data)",
        f"- Generated: {now.isoformat(timespec='seconds')}",
        f"- Conjunctions flagged: {len(results)}", "",
    ]
    for i, e in enumerate(results, 1):
        trend_str = (
            f" (Pc ×{e['trend']['pc_change_ratio']} across {e['trend']['observations']} observations)"
            if e["trend"]["pc_change_ratio"] is not None
            else f" ({e['trend']['observations']} observation(s) so far)"
        )
        md_lines += [
            f"## {i}. {e['object_a']} vs {e['object_b']} — {e['priority_tier']} ({e['priority_score']}/100)",
            "",
            f"- NORAD IDs: {e['norad_a']} / {e['norad_b']}",
            f"- TCA (UTC): {e['time_utc']}",
            f"- Miss distance: **{e['miss_distance_km']} km**",
            f"- Probability of collision (real, SOCRATES): **{e['probability_of_collision']:.3e}**",
            f"- Priority breakdown: Pc={e['score_breakdown']['pc_score']}, "
            f"urgency={e['score_breakdown']['urgency_score']}, freshness={e['score_breakdown']['freshness_score']}",
            f"- Trend: **{e['trend']['direction']}**{trend_str}",
            "",
            f"**{e['analysis']['summary']}**",
            "",
            f"*Why it matters*: {e['analysis']['why_it_matters']}",
            "",
            f"*Trend*: {e['analysis']['trend_explanation']}",
            "",
            f"*Suggested next step*: {e['analysis']['suggested_next_step']}",
            "",
            f"*Confidence*: {e['analysis']['confidence']} ({e['analysis']['source']})",
            "",
        ]
        if e["analysis"]["limitations"]:
            md_lines.append("*Limitations*: " + "; ".join(e["analysis"]["limitations"]))
            md_lines.append("")

    report_text = "\n".join(md_lines)
    with open(args.output, "w") as f:
        f.write(report_text)

    json_output = str(args.output).rsplit(".", 1)[0] + ".json"
    with open(json_output, "w") as f:
        json.dump({
            "source_label": "CelesTrak SOCRATES Plus (real conjunction data)",
            "generated_at": now.isoformat(timespec="seconds"),
            "conjunctions_flagged": len(results),
            "events": results,
        }, f, indent=2)
    print(f"      Also wrote structured summary to {json_output}")

    repo.close()
    print("\nDone.")
    print(report_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

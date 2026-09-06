#!/usr/bin/env python3
"""
run_baseline.py
----------------
End-to-end CLI for the Orbital Collision-Risk Agent baseline.

Pipeline (multi-tool agentic workflow):
  1. tle_loader.load_catalog        -> parse TLE file into satellite objects
  2. conjunction.screen_conjunctions -> propagate + screen for close approaches
  3. knowledge_base.KnowledgeBase    -> retrieve relevant operational notes (RAG)
  4. reasoning_agent.generate_event_report -> LLM (or rule-based) risk write-up
  5. report.render_report            -> assemble final Markdown report

Example:
    python run_baseline.py --input data/sample_catalog.tle --output report.md
"""
from __future__ import annotations

import argparse
import sys

from src.conjunction import screen_conjunctions
from src.knowledge_base import KnowledgeBase
from src.live_fetch import LiveFetchError, fetch_live_catalog
from src.reasoning_agent import generate_event_report
from src.report import render_json, render_report
from src.tle_loader import load_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Orbital Collision-Risk Agent baseline")
    parser.add_argument("--input", default="data/sample_catalog.tle", help="Path to a TLE catalog file (ignored if --live is set)")
    parser.add_argument("--live", action="store_true", help="Fetch a live catalog from Celestrak instead of using --input")
    parser.add_argument("--live-group", default="stations", help="Celestrak GROUP to fetch when --live is set (e.g. stations, active, debris)")
    parser.add_argument("--output", default="report.md", help="Path to write the Markdown report to")
    parser.add_argument("--lookahead-seconds", type=int, default=6000, help="How far ahead to screen")
    parser.add_argument("--step-seconds", type=int, default=1, help="Sampling step for screening")
    parser.add_argument("--flag-threshold-km", type=float, default=25.0, help="Miss distance below which an event is flagged")
    args = parser.parse_args()

    if args.live:
        print(f"[0/4] Fetching live catalog (group={args.live_group}) from Celestrak ...")
        try:
            input_path = fetch_live_catalog(group=args.live_group)
        except LiveFetchError as e:
            print(f"      Live fetch failed: {e}")
            return 1
        print(f"      Cached at {input_path}")
    else:
        input_path = args.input

    print(f"[1/4] Loading TLE catalog from {input_path} ...")
    catalog = load_catalog(input_path)
    print(f"      Loaded {len(catalog)} object(s): {[o.name for o in catalog]}")

    print(f"[2/4] Screening for conjunctions over {args.lookahead_seconds}s window ...")
    events = screen_conjunctions(
        catalog,
        lookahead_seconds=args.lookahead_seconds,
        step_seconds=args.step_seconds,
        flag_threshold_km=args.flag_threshold_km,
    )
    print(f"      Flagged {len(events)} conjunction(s) under {args.flag_threshold_km} km")

    print("[3/4] Retrieving grounding notes and generating risk assessments ...")
    kb = KnowledgeBase()
    assessments = [generate_event_report(e, kb) for e in events]

    print(f"[4/4] Writing report to {args.output} ...")
    report_text = render_report(str(input_path), assessments)
    with open(args.output, "w") as f:
        f.write(report_text)

    json_output = str(args.output).rsplit(".", 1)[0] + ".json"
    with open(json_output, "w") as f:
        f.write(render_json(str(input_path), assessments))
    print(f"      Also wrote structured summary to {json_output}")

    print("\nDone.")
    print(report_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

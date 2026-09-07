#!/usr/bin/env python3
"""
run_triage.py
--------------
Phase 2: the accessible triage layer, built on REAL conjunction data.

This does not reimplement conjunction screening — CelesTrak's SOCRATES Plus
has done full-catalog screening for free since 2004 with real covariance,
and open-source projects like SIMPLETON already do all-vs-all screening
validated against it (see docs/RESEARCH.md). What's missing from both is a
layer that turns a table of numbers into something a satellite operator or
student *without a dedicated SSA analyst* can actually act on. That's what
this script does:

  1. socrates_client.fetch_conjunctions -> pull real, published conjunction
     data (real Pc, real covariance, computed by STK/CAT)
  2. triage.prioritize                  -> filter/sort by real risk
  3. triage.from_socrates               -> adapt into this project's
                                            existing ConjunctionEvent type
  4. knowledge_base + reasoning_agent   -> the same grounding + narrative
                                            layer as the phase 1 baseline,
                                            reused unchanged
  5. report.render_report/render_json   -> same output format as phase 1,
                                            with real-data provenance
                                            labeled throughout

Example:
    python run_triage.py --max-results 50 --min-probability 1e-6 --output triage_report.md
"""
from __future__ import annotations

import argparse
import sys

from src.knowledge_base import KnowledgeBase
from src.reasoning_agent import generate_event_report
from src.report import render_json, render_report
from src.socrates_client import SocratesFetchError, fetch_conjunctions
from src.triage import from_socrates, prioritize


def main() -> int:
    parser = argparse.ArgumentParser(description="Real-data conjunction triage layer (phase 2)")
    parser.add_argument("--max-results", type=int, default=50, help="Max conjunctions to fetch from SOCRATES Plus")
    parser.add_argument("--min-probability", type=float, default=0.0, help="Drop events below this probability of collision")
    parser.add_argument("--limit", type=int, default=20, help="Max events to run the full triage/LLM pass on (keeps runtime and API cost bounded)")
    parser.add_argument("--output", default="triage_report.md", help="Path to write the Markdown report to")
    args = parser.parse_args()

    print(f"[1/4] Fetching up to {args.max_results} real conjunctions from CelesTrak SOCRATES Plus ...")
    try:
        records = fetch_conjunctions(max_results=args.max_results, order="MAXPROB")
    except SocratesFetchError as e:
        print(f"      Fetch failed: {e}")
        print("      (This is expected in network-restricted environments — see README.)")
        return 1
    print(f"      Retrieved {len(records)} real conjunction record(s)")

    print(f"[2/4] Prioritizing (min probability={args.min_probability}, limit={args.limit}) ...")
    prioritized = prioritize(records, min_probability=args.min_probability, limit=args.limit)
    events = [from_socrates(r) for r in prioritized]
    print(f"      Triaging {len(events)} event(s)")

    print("[3/4] Retrieving grounding notes and generating risk assessments ...")
    kb = KnowledgeBase()
    assessments = [generate_event_report(e, kb) for e in events]

    print(f"[4/4] Writing report to {args.output} ...")
    source_label = "CelesTrak SOCRATES Plus (real conjunction data, STK/CAT propagation, real covariance)"
    report_text = render_report(source_label, assessments)
    with open(args.output, "w") as f:
        f.write(report_text)

    json_output = str(args.output).rsplit(".", 1)[0] + ".json"
    with open(json_output, "w") as f:
        f.write(render_json(source_label, assessments))
    print(f"      Also wrote structured summary to {json_output}")

    print("\nDone.")
    print(report_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

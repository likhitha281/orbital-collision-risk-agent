"""
orchestration/prefect_flow.py
------------------------------
The same pipeline as run_baseline.py, but expressed as a Prefect flow
instead of a linear script. This is what you reach for when a plain cron
job (GitHub Actions, Ofelia, a Kubernetes CronJob) stops being enough:

  * Per-task retries: if the live fetch fails transiently, only that task
    retries — you don't re-run the whole pipeline (and you don't re-hit
    the network for tasks that already succeeded).
  * A visible task graph: Prefect's UI shows exactly which step failed and
    why, instead of a wall of stdout in a CI log.
  * Parametrized runs: trigger a run with different arguments (a different
    Celestrak group, a different threshold) without editing a workflow file.
  * A real scheduler process (or Prefect Cloud's free tier) instead of
    relying on your CI provider's cron semantics.

None of this is necessary at this project's current scale — a GitHub Actions
cron job is genuinely fine for one source, one screening job, every 4 hours.
This is here to show the next step if the pipeline grows (multiple data
sources, dependent jobs, backfills, alerting on failure) and to make that
tradeoff concrete rather than abstract. See the README's "Docker & other
orchestration options" section for the comparison.

Run locally (ephemeral, no server needed):
    pip install prefect
    python orchestration/prefect_flow.py

Deploy on a schedule (requires `prefect server start` or Prefect Cloud):
    prefect deployment build orchestration/prefect_flow.py:collision_risk_flow \
        --name live-4h --cron "0 */4 * * *"
    prefect deployment apply collision_risk_flow-deployment.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prefect import flow, get_run_logger, task
from prefect.cache_policies import NO_CACHE

from src.conjunction import screen_conjunctions
from src.knowledge_base import KnowledgeBase
from src.live_fetch import LiveFetchError, fetch_live_catalog
from src.reasoning_agent import generate_event_report
from src.report import render_json, render_report
from src.tle_loader import load_catalog


@task(retries=3, retry_delay_seconds=30)
def fetch_catalog_task(live: bool, live_group: str, static_input: str) -> str:
    """Retries matter here specifically: this is the one task that hits an
    external network dependency and can fail transiently."""
    logger = get_run_logger()
    if not live:
        logger.info(f"Using static catalog: {static_input}")
        return static_input
    try:
        path = fetch_live_catalog(group=live_group)
        logger.info(f"Fetched live catalog: {path}")
        return str(path)
    except LiveFetchError as e:
        logger.error(f"Live fetch failed: {e}")
        raise


@task
def load_catalog_task(path: str):
    return load_catalog(path)


@task(cache_policy=NO_CACHE)
def screen_conjunctions_task(catalog, lookahead_seconds: int, step_seconds: int, flag_threshold_km: float):
    # NO_CACHE: `catalog` holds Skyfield EarthSatellite objects, which wrap
    # a non-picklable C extension type (Satrec) — Prefect can't hash them
    # for caching, and doesn't need to here (this task is cheap enough to
    # just re-run rather than cache).
    return screen_conjunctions(
        catalog,
        lookahead_seconds=lookahead_seconds,
        step_seconds=step_seconds,
        flag_threshold_km=flag_threshold_km,
    )


@task
def assess_events_task(events):
    kb = KnowledgeBase()
    return [generate_event_report(e, kb) for e in events]


@task
def write_reports_task(catalog_path: str, assessments: list, output_path: str):
    md = render_report(catalog_path, assessments)
    Path(output_path).write_text(md)

    json_path = str(output_path).rsplit(".", 1)[0] + ".json"
    Path(json_path).write_text(render_json(catalog_path, assessments))
    return output_path, json_path


@flow(name="orbital-collision-risk")
def collision_risk_flow(
    live: bool = False,
    live_group: str = "stations",
    static_input: str = "data/sample_catalog.tle",
    output_path: str = "report.md",
    lookahead_seconds: int = 6000,
    step_seconds: int = 1,
    flag_threshold_km: float = 25.0,
):
    logger = get_run_logger()

    catalog_path = fetch_catalog_task(live, live_group, static_input)
    catalog = load_catalog_task(catalog_path)
    events = screen_conjunctions_task(catalog, lookahead_seconds, step_seconds, flag_threshold_km)
    assessments = assess_events_task(events)
    md_path, json_path = write_reports_task(catalog_path, assessments, output_path)

    logger.info(f"Flagged {len(events)} conjunction(s). Reports: {md_path}, {json_path}")
    return {"flagged": len(events), "report_md": md_path, "report_json": json_path}


if __name__ == "__main__":
    result = collision_risk_flow(live=False, output_path="output/report.md")
    print(result)

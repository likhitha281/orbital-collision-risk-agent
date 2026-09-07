"""
triage.py
---------
Adapts real SOCRATES Plus conjunction records into this project's existing
ConjunctionEvent / reasoning_agent / report pipeline, so the exact same
downstream code (risk tiering, knowledge-base grounding, LLM narrative,
Markdown/JSON rendering) works whether the events came from our own SGP4
baseline or from CelesTrak's real screening run.
"""
from __future__ import annotations

from .conjunction import ConjunctionEvent
from .socrates_client import SocratesConjunction

# DSE (days since epoch) beyond this is flagged as stale — see the
# "tracking-uncertainty" knowledge-base note. This doesn't drop the event,
# it just gets surfaced so the analyst / LLM can weight it appropriately.
STALE_DSE_DAYS = 7.0


def from_socrates(record: SocratesConjunction) -> ConjunctionEvent:
    return ConjunctionEvent(
        object_a=record.object_name_1,
        object_b=record.object_name_2,
        norad_a=record.norad_id_1,
        norad_b=record.norad_id_2,
        time_utc=record.tca_utc,
        miss_distance_km=record.miss_distance_km,
        relative_speed_km_s=record.relative_speed_km_s,
        involves_synthetic=False,
        probability_of_collision=record.max_probability,
        pc_provenance="socrates_real",
        stale_tle=is_stale(record),
    )


def is_stale(record: SocratesConjunction, max_dse_days: float = STALE_DSE_DAYS) -> bool:
    return max(record.days_since_epoch_1, record.days_since_epoch_2) > max_dse_days


def prioritize(
    records: list[SocratesConjunction],
    min_probability: float = 0.0,
    limit: int | None = None,
) -> list[SocratesConjunction]:
    """Filter and sort real conjunctions for triage: highest probability of
    collision first, since that's the number an analyst without time to
    review everything should see at the top."""
    filtered = [r for r in records if r.max_probability >= min_probability]
    filtered.sort(key=lambda r: r.max_probability, reverse=True)
    return filtered[:limit] if limit else filtered

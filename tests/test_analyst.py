import sys
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analyst import AnalystOutput, explain
from src.observation_store import Observation
from src.risk_scoring import assess
from datetime import datetime, timedelta, timezone
from src.trends import RiskTrend

NOW = datetime(2026, 9, 10, tzinfo=timezone.utc)


def _obs(pc: float, dse1=0.5, dse2=1.0) -> Observation:
    return Observation(
        norad_id_1="25544", norad_id_2="90001",
        object_name_1="ISS (ZARYA)", object_name_2="TEST FRAGMENT",
        tca_utc=(NOW + timedelta(hours=10)).isoformat(),
        observed_at=NOW.isoformat(),
        miss_distance_km=1.2, relative_speed_km_s=7.5,
        probability_of_collision=pc,
        days_since_epoch_1=dse1, days_since_epoch_2=dse2,
    )


def test_analyst_output_schema_has_no_numeric_override_field():
    # The actual enforcement: there is structurally nowhere to put an
    # altered probability or priority score.
    field_names = {f.name for f in fields(AnalystOutput)}
    forbidden = {"probability_of_collision", "priority_score", "priority", "pc", "tier"}
    assert field_names.isdisjoint(forbidden)


def test_fallback_never_invents_a_different_pc_value():
    obs = _obs(pc=2.34e-4)
    assessment = assess(obs.probability_of_collision, NOW + timedelta(hours=10), 1.0, now=NOW)
    trend = RiskTrend(direction="insufficient_data", pc_change_ratio=None, miss_distance_change_km=None, observations=1)

    result = explain(obs, assessment, trend)

    assert result.source == "rule_based_fallback"  # no ANTHROPIC_API_KEY in test env
    assert f"{obs.probability_of_collision:.2e}" in result.summary


def test_fallback_reflects_the_given_priority_tier_verbatim():
    obs = _obs(pc=5e-3)  # will score HIGH
    assessment = assess(obs.probability_of_collision, NOW + timedelta(hours=1), 0.5, now=NOW)
    trend = RiskTrend(direction="insufficient_data", pc_change_ratio=None, miss_distance_change_km=None, observations=1)

    result = explain(obs, assessment, trend)

    assert assessment.priority_tier in result.summary
    assert assessment.priority_tier == "HIGH"


def test_fallback_escalation_ratio_matches_trend_exactly():
    obs = _obs(pc=1e-4)
    assessment = assess(obs.probability_of_collision, NOW + timedelta(hours=10), 1.0, now=NOW)
    trend = RiskTrend(direction="escalating", pc_change_ratio=42.0, miss_distance_change_km=-1.5, observations=3)

    result = explain(obs, assessment, trend)

    assert "42.0" in result.trend_explanation


def test_stale_data_surfaces_in_limitations():
    obs = _obs(pc=1e-5, dse1=9.0, dse2=1.0)  # max DSE = 9 days, > 7-day threshold
    assessment = assess(obs.probability_of_collision, NOW + timedelta(hours=10), 9.0, now=NOW)
    trend = RiskTrend(direction="insufficient_data", pc_change_ratio=None, miss_distance_change_km=None, observations=1)

    result = explain(obs, assessment, trend)

    assert any("7 days" in lim for lim in result.limitations)
    assert result.confidence == "low"

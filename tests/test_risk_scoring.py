import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.risk_scoring import assess

NOW = datetime(2026, 9, 10, tzinfo=timezone.utc)


def test_higher_pc_increases_priority_score():
    low = assess(probability_of_collision=1e-8, tca_utc=NOW + timedelta(hours=48), max_days_since_epoch=1, now=NOW)
    high = assess(probability_of_collision=1e-3, tca_utc=NOW + timedelta(hours=48), max_days_since_epoch=1, now=NOW)
    assert high.priority_score > low.priority_score
    assert high.pc_score > low.pc_score


def test_shorter_tca_increases_urgency_and_score():
    far = assess(probability_of_collision=1e-5, tca_utc=NOW + timedelta(hours=70), max_days_since_epoch=1, now=NOW)
    near = assess(probability_of_collision=1e-5, tca_utc=NOW + timedelta(hours=2), max_days_since_epoch=1, now=NOW)
    assert near.urgency_score > far.urgency_score
    assert near.priority_score > far.priority_score


def test_stale_data_lowers_score_not_raises_it():
    fresh = assess(probability_of_collision=1e-5, tca_utc=NOW + timedelta(hours=24), max_days_since_epoch=0.5, now=NOW)
    stale = assess(probability_of_collision=1e-5, tca_utc=NOW + timedelta(hours=24), max_days_since_epoch=10, now=NOW)
    assert stale.freshness_score < fresh.freshness_score
    assert stale.priority_score < fresh.priority_score


def test_near_zero_pc_does_not_produce_high_tier():
    # This is the exact scenario the review flagged: Pc=7.8e-22 must not
    # come out HIGH or MEDIUM regardless of other factors.
    result = assess(probability_of_collision=7.8e-22, tca_utc=NOW + timedelta(hours=1), max_days_since_epoch=0.1, now=NOW)
    assert result.priority_tier == "LOW"


def test_high_pc_and_near_tca_produces_high_tier():
    result = assess(probability_of_collision=1e-3, tca_utc=NOW + timedelta(hours=2), max_days_since_epoch=0.5, now=NOW)
    assert result.priority_tier == "HIGH"


def test_reasons_are_never_empty():
    result = assess(probability_of_collision=1e-6, tca_utc=NOW + timedelta(hours=30), max_days_since_epoch=3, now=NOW)
    assert len(result.reasons) >= 1

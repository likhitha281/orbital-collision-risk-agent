import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.observation_store import Observation
from src.trends import calculate_trend


def _obs(pc: float, miss_km: float, observed_at: str) -> Observation:
    return Observation(
        norad_id_1="25544", norad_id_2="90001",
        object_name_1="ISS", object_name_2="DEBRIS",
        tca_utc="2026-09-10T04:12:33", observed_at=observed_at,
        miss_distance_km=miss_km, relative_speed_km_s=7.5,
        probability_of_collision=pc,
        days_since_epoch_1=0.5, days_since_epoch_2=1.0,
    )


def test_single_observation_is_insufficient_data():
    trend = calculate_trend([_obs(1e-5, 2.0, "t1")])
    assert trend.direction == "insufficient_data"
    assert trend.pc_change_ratio is None


def test_detects_escalation():
    history = [_obs(1e-6, 2.0, "t1"), _obs(5e-5, 0.6, "t2")]  # 50x increase
    trend = calculate_trend(history)
    assert trend.direction == "escalating"
    assert trend.pc_change_ratio == 50.0


def test_detects_decrease():
    history = [_obs(1e-4, 2.0, "t1"), _obs(1e-6, 5.0, "t2")]  # 100x decrease
    trend = calculate_trend(history)
    assert trend.direction == "decreasing"


def test_small_change_is_stable():
    history = [_obs(1e-5, 2.0, "t1"), _obs(1.2e-5, 1.9, "t2")]  # 1.2x — within stable band
    trend = calculate_trend(history)
    assert trend.direction == "stable"


def test_uses_oldest_and_newest_not_just_last_two():
    # Middle observation is noisy/lower, but oldest vs newest still shows escalation
    history = [_obs(1e-6, 2.0, "t1"), _obs(2e-7, 3.0, "t2"), _obs(5e-5, 0.5, "t3")]
    trend = calculate_trend(history)
    assert trend.direction == "escalating"
    assert trend.observations == 3


def test_zero_oldest_pc_gives_none_ratio_not_crash():
    history = [_obs(0.0, 2.0, "t1"), _obs(1e-5, 1.0, "t2")]
    trend = calculate_trend(history)
    assert trend.pc_change_ratio is None
    assert trend.direction == "stable"  # can't compute ratio, so no escalation claim is made

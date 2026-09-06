import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.probability_of_collision import compute_pc


def test_pc_decreases_with_miss_distance():
    close = compute_pc(miss_distance_km=0.05)
    far = compute_pc(miss_distance_km=5.0)
    assert close.probability > far.probability


def test_pc_is_a_valid_probability():
    result = compute_pc(miss_distance_km=0.1)
    assert 0.0 <= result.probability <= 1.0


def test_pc_flags_covariance_as_assumed():
    result = compute_pc(miss_distance_km=1.0)
    assert result.is_covariance_assumed is True

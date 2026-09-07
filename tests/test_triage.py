import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.socrates_client import SocratesConjunction
from src.triage import from_socrates, is_stale, prioritize

FRESH = SocratesConjunction(
    norad_id_1="25544", object_name_1="ISS (ZARYA) [+]", days_since_epoch_1=0.5,
    norad_id_2="90001", object_name_2="TEST FRAGMENT A [-]", days_since_epoch_2=1.0,
    tca_utc="2026-09-10T04:12:33Z", miss_distance_km=1.2, relative_speed_km_s=7.5,
    max_probability=2e-4, dilution="0.5",
)

STALE = SocratesConjunction(
    norad_id_1="33591", object_name_1="NOAA 19 [+]", days_since_epoch_1=10.0,
    norad_id_2="90002", object_name_2="TEST FRAGMENT B [-]", days_since_epoch_2=1.0,
    tca_utc="2026-09-11T10:00:00Z", miss_distance_km=4.5, relative_speed_km_s=7.4,
    max_probability=5e-7, dilution="0.9",
)


def test_from_socrates_sets_real_provenance():
    event = from_socrates(FRESH)
    assert event.pc_provenance == "socrates_real"
    assert event.involves_synthetic is False
    assert event.probability_of_collision == 2e-4


def test_is_stale_uses_max_of_both_objects():
    assert is_stale(FRESH, max_dse_days=7.0) is False
    assert is_stale(STALE, max_dse_days=7.0) is True


def test_from_socrates_flags_staleness():
    assert from_socrates(STALE).stale_tle is True
    assert from_socrates(FRESH).stale_tle is False


def test_prioritize_filters_and_sorts_by_probability():
    result = prioritize([STALE, FRESH], min_probability=1e-6)
    assert len(result) == 1
    assert result[0] is FRESH  # STALE's 5e-7 probability is below the filter


def test_prioritize_sorts_highest_probability_first():
    result = prioritize([FRESH, STALE], min_probability=0.0)
    assert result[0] is FRESH
    assert result[1] is STALE

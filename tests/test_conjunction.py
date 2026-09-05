import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.conjunction import screen_conjunctions
from src.tle_loader import load_catalog

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_catalog.tle"


def test_loads_two_objects():
    catalog = load_catalog(SAMPLE)
    assert len(catalog) == 2
    names = {o.name for o in catalog}
    assert "ISS (ZARYA)" in names


def test_finds_the_seeded_conjunction():
    catalog = load_catalog(SAMPLE)
    events = screen_conjunctions(catalog, lookahead_seconds=6000, step_seconds=1, flag_threshold_km=25.0)
    assert len(events) == 1
    event = events[0]
    assert event.miss_distance_km < 5.0
    assert event.involves_synthetic is True


def test_no_events_with_tight_threshold_and_far_objects():
    catalog = load_catalog(SAMPLE)
    # An absurdly tight threshold on a short window should find nothing to flag
    events = screen_conjunctions(catalog, lookahead_seconds=100, step_seconds=1, flag_threshold_km=0.001)
    assert events == []

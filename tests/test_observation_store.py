import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.observation_store import ObservationRepository, pair_key
from src.socrates_client import SocratesConjunction

REC = SocratesConjunction(
    norad_id_1="25544", object_name_1="ISS (ZARYA)", days_since_epoch_1=0.5,
    norad_id_2="90001", object_name_2="TEST FRAGMENT", days_since_epoch_2=1.0,
    tca_utc="2026-09-10T04:12:33", miss_distance_km=1.2, relative_speed_km_s=7.5,
    max_probability=2e-4, dilution="0.5",
)


def test_pair_key_is_order_independent():
    assert pair_key("A", "B") == pair_key("B", "A")


def test_save_and_retrieve_history(tmp_path):
    with ObservationRepository(tmp_path / "test.db") as repo:
        inserted = repo.save_many([REC], observed_at="2026-09-01T00:00:00")
        assert inserted == 1
        history = repo.history_for("25544", "90001", "2026-09-10T04:12:33")
        assert len(history) == 1
        assert history[0].probability_of_collision == 2e-4


def test_history_lookup_is_order_independent(tmp_path):
    with ObservationRepository(tmp_path / "test.db") as repo:
        repo.save_many([REC], observed_at="2026-09-01T00:00:00")
        # query with ids swapped from how the record was stored
        history = repo.history_for("90001", "25544", "2026-09-10T04:12:33")
        assert len(history) == 1


def test_duplicate_observation_is_not_inserted_twice(tmp_path):
    with ObservationRepository(tmp_path / "test.db") as repo:
        first = repo.save_many([REC], observed_at="2026-09-01T00:00:00")
        second = repo.save_many([REC], observed_at="2026-09-01T00:00:00")  # same observed_at = exact duplicate
        assert first == 1
        assert second == 0
        assert len(repo.history_for("25544", "90001", "2026-09-10T04:12:33")) == 1


def test_multiple_observed_at_accumulate_history(tmp_path):
    with ObservationRepository(tmp_path / "test.db") as repo:
        repo.save_many([REC], observed_at="2026-09-01T00:00:00")
        repo.save_many([REC], observed_at="2026-09-01T04:00:00")  # different observed_at = new snapshot
        history = repo.history_for("25544", "90001", "2026-09-10T04:12:33")
        assert len(history) == 2
        assert history[0].observed_at < history[1].observed_at  # oldest first

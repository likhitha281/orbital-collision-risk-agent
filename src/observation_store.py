"""
observation_store.py
---------------------
SQLite-backed history of real SOCRATES observations, keyed by object pair
and TCA. This is what actually enables the agent to reason about *change*
("Pc increased 40x since the last check") instead of only ever narrating a
single snapshot — that gap, not model choice, is why the v1 agent read as
a wrapper rather than something that reasons.

Deliberately stdlib-only (sqlite3): this project's scale (dozens of events,
polled every few hours by the scheduled workflow) doesn't justify Postgres,
SQLAlchemy, or anything heavier. Each run of run_triage.py appends new
observations; nothing is ever overwritten, so history accumulates.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .socrates_client import SocratesConjunction

DEFAULT_DB_PATH = Path("data/orbital_history.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    norad_id_1 TEXT NOT NULL,
    norad_id_2 TEXT NOT NULL,
    object_name_1 TEXT,
    object_name_2 TEXT,
    tca_utc TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    miss_distance_km REAL NOT NULL,
    relative_speed_km_s REAL,
    probability_of_collision REAL NOT NULL,
    days_since_epoch_1 REAL,
    days_since_epoch_2 REAL,
    source TEXT NOT NULL DEFAULT 'socrates',
    UNIQUE(norad_id_1, norad_id_2, tca_utc, observed_at)
);
CREATE INDEX IF NOT EXISTS idx_pair_tca ON observations(norad_id_1, norad_id_2, tca_utc);
"""


@dataclass(frozen=True)
class Observation:
    norad_id_1: str
    norad_id_2: str
    object_name_1: str
    object_name_2: str
    tca_utc: str
    observed_at: str
    miss_distance_km: float
    relative_speed_km_s: float
    probability_of_collision: float
    days_since_epoch_1: float
    days_since_epoch_2: float
    source: str = "socrates"


def pair_key(a: str, b: str) -> tuple[str, str]:
    """Order-independent key so 'A vs B' and 'B vs A' are treated as the
    same event across runs, regardless of which order SOCRATES lists them."""
    lo, hi = sorted([a, b])
    return lo, hi


class ObservationRepository:
    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def save_many(self, records: list[SocratesConjunction], observed_at: str | None = None) -> int:
        """Insert this batch as one observation snapshot. Returns the number
        of genuinely new rows inserted (duplicates — same pair, TCA, and
        observed_at — are silently skipped, not errors)."""
        observed_at = observed_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        inserted = 0
        for r in records:
            id1, id2 = pair_key(r.norad_id_1, r.norad_id_2)
            if id1 == r.norad_id_1:
                name1, name2 = r.object_name_1, r.object_name_2
                dse1, dse2 = r.days_since_epoch_1, r.days_since_epoch_2
            else:
                name1, name2 = r.object_name_2, r.object_name_1
                dse1, dse2 = r.days_since_epoch_2, r.days_since_epoch_1
            try:
                self._conn.execute(
                    "INSERT INTO observations "
                    "(norad_id_1, norad_id_2, object_name_1, object_name_2, tca_utc, observed_at, "
                    " miss_distance_km, relative_speed_km_s, probability_of_collision, "
                    " days_since_epoch_1, days_since_epoch_2, source) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (id1, id2, name1, name2, r.tca_utc, observed_at,
                     r.miss_distance_km, r.relative_speed_km_s, r.max_probability,
                     dse1, dse2, "socrates"),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                pass  # exact duplicate of an existing observation — expected on reruns
        self._conn.commit()
        return inserted

    def history_for(self, norad_id_1: str, norad_id_2: str, tca_utc: str) -> list[Observation]:
        """Full observation history for one object pair + TCA, oldest first."""
        id1, id2 = pair_key(norad_id_1, norad_id_2)
        cur = self._conn.execute(
            "SELECT norad_id_1, norad_id_2, object_name_1, object_name_2, tca_utc, observed_at, "
            "miss_distance_km, relative_speed_km_s, probability_of_collision, "
            "days_since_epoch_1, days_since_epoch_2, source "
            "FROM observations WHERE norad_id_1=? AND norad_id_2=? AND tca_utc=? "
            "ORDER BY observed_at ASC",
            (id1, id2, tca_utc),
        )
        return [Observation(*row) for row in cur.fetchall()]

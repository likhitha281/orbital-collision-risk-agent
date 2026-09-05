"""
tle_loader.py
--------------
Tool #1 in the agent's toolchain: loads Two-Line Element (TLE) sets from a
text file and turns them into Skyfield EarthSatellite objects that the
propagation tool can use.

TLE files are expected in the standard 3-line-per-object format:

    <NAME>
    1 NNNNNU ...
    2 NNNNN  ...

Real catalog data can be downloaded from public sources such as
https://celestrak.org/NORAD/elements/ . This project ships a small sample
catalog (data/sample_catalog.tle) so the baseline is runnable offline.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skyfield.api import EarthSatellite, load


@dataclass
class CatalogObject:
    name: str
    norad_id: str
    satellite: EarthSatellite
    is_synthetic: bool


def _is_synthetic(name: str, line1: str) -> bool:
    """Flag objects that are clearly test/synthetic fixtures rather than
    real cataloged objects (used so reports can label them honestly)."""
    return "SYNTHETIC" in name.upper() or line1[2:7].strip() == "99999"


def load_catalog(path: str | Path) -> list[CatalogObject]:
    """Parse a TLE text file into a list of CatalogObject.

    Raises ValueError if the file is malformed (wrong number of lines).
    """
    path = Path(path)
    lines = [ln.rstrip("\n") for ln in path.read_text().splitlines() if ln.strip()]

    if len(lines) % 3 != 0:
        raise ValueError(
            f"{path} does not look like a valid 3-line-per-object TLE file "
            f"(found {len(lines)} non-blank lines, expected a multiple of 3)"
        )

    ts = load.timescale()
    objects: list[CatalogObject] = []
    for i in range(0, len(lines), 3):
        name, line1, line2 = lines[i], lines[i + 1], lines[i + 2]
        norad_id = line1[2:7].strip()
        sat = EarthSatellite(line1, line2, name, ts)
        objects.append(
            CatalogObject(
                name=name.strip(),
                norad_id=norad_id,
                satellite=sat,
                is_synthetic=_is_synthetic(name, line1),
            )
        )
    return objects

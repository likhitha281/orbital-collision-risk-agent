import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.socrates_client import fetch_conjunctions, SocratesFetchError, EXPECTED_HEADER

# Fixture data: matches CelesTrak's documented SOCRATES Plus CSV schema
# exactly (https://celestrak.org/SOCRATES/socrates-format.php), but the
# values themselves are made up for testing — NOT a real, current
# conjunction. ISS's real catalog number (25544) is used for realism; the
# second object and all numeric values are fabricated test fixtures.
SAMPLE_CSV = (
    "NORAD_CAT_ID_1,OBJECT_NAME_1,DSE_1,NORAD_CAT_ID_2,OBJECT_NAME_2,DSE_2,"
    "TCA,TCA_RANGE,TCA_RELATIVE_SPEED,MAX_PROB,DILUTION\n"
    "25544,ISS (ZARYA) [+],0.5,90001,TEST FRAGMENT A [-],2.1,"
    "2026-09-10T04:12:33.000000,1.234,7.891,0.00023,0.5\n"
    "33591,NOAA 19 [+],1.0,90002,TEST FRAGMENT B [-],9.0,"
    "2026-09-11T10:00:00.000000,4.500,7.400,0.0000005,0.9\n"
)

MALFORMED_CSV = "WRONG,HEADER,ROW\n1,2,3\n"


def _mock_response(text: str):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = text.encode()
    return cm


def test_fetches_and_parses(tmp_path):
    cache = tmp_path / "socrates.csv"
    with patch("urllib.request.urlopen", return_value=_mock_response(SAMPLE_CSV)):
        records = fetch_conjunctions(cache_path=cache, force=True)
    assert len(records) == 2
    assert records[0].norad_id_1 == "25544"
    assert records[0].object_name_1 == "ISS (ZARYA) [+]"
    assert records[0].max_probability == 0.00023


def test_caches_and_skips_refetch(tmp_path):
    cache = tmp_path / "socrates.csv"
    with patch("urllib.request.urlopen", return_value=_mock_response(SAMPLE_CSV)) as mock_urlopen:
        fetch_conjunctions(cache_path=cache, force=True)
        fetch_conjunctions(cache_path=cache, min_refetch_seconds=3600)
        assert mock_urlopen.call_count == 1


def test_rejects_unexpected_header(tmp_path):
    cache = tmp_path / "socrates.csv"
    with patch("urllib.request.urlopen", return_value=_mock_response(MALFORMED_CSV)):
        try:
            fetch_conjunctions(cache_path=cache, force=True)
            assert False, "expected SocratesFetchError"
        except SocratesFetchError:
            pass


def test_expected_header_matches_documented_schema():
    # Guards against silent drift from CelesTrak's documented format.
    assert EXPECTED_HEADER == [
        "NORAD_CAT_ID_1", "OBJECT_NAME_1", "DSE_1",
        "NORAD_CAT_ID_2", "OBJECT_NAME_2", "DSE_2",
        "TCA", "TCA_RANGE", "TCA_RELATIVE_SPEED", "MAX_PROB", "DILUTION",
    ]

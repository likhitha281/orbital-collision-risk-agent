import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.live_fetch import fetch_live_catalog, LiveFetchError

SAMPLE_TLE_TEXT = (
    "ISS (ZARYA)\n"
    "1 25544U 98067A   25308.35786713  .00010709  00000+0  19707-3 0  9991\n"
    "2 25544  51.6336 332.4903 0005031  16.0382 344.0765 15.49743270536903\n"
)


def _mock_response(text: str):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = text.encode()
    return cm


def test_fetches_and_caches(tmp_path):
    with patch("urllib.request.urlopen", return_value=_mock_response(SAMPLE_TLE_TEXT)) as mock_urlopen:
        path = fetch_live_catalog(group="stations", cache_dir=tmp_path, force=True)
        assert path.exists()
        assert "ISS" in path.read_text()
        assert mock_urlopen.call_count == 1


def test_does_not_refetch_within_min_interval(tmp_path):
    with patch("urllib.request.urlopen", return_value=_mock_response(SAMPLE_TLE_TEXT)) as mock_urlopen:
        fetch_live_catalog(group="stations", cache_dir=tmp_path, force=True)
        fetch_live_catalog(group="stations", cache_dir=tmp_path, min_refetch_seconds=3600)
        assert mock_urlopen.call_count == 1  # second call should hit the cache, not the network


def test_raises_if_no_cache_and_network_fails(tmp_path):
    with patch("urllib.request.urlopen", side_effect=RuntimeError("network down")):
        try:
            fetch_live_catalog(group="stations", cache_dir=tmp_path, force=True)
            assert False, "expected LiveFetchError"
        except LiveFetchError:
            pass


def test_falls_back_to_stale_cache_on_network_failure(tmp_path):
    with patch("urllib.request.urlopen", return_value=_mock_response(SAMPLE_TLE_TEXT)):
        path = fetch_live_catalog(group="stations", cache_dir=tmp_path, force=True)

    with patch("urllib.request.urlopen", side_effect=RuntimeError("network down")):
        path2 = fetch_live_catalog(group="stations", cache_dir=tmp_path, force=True)
        assert path2 == path
        assert "ISS" in path2.read_text()

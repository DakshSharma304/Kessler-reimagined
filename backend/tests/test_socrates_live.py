"""Stage 2 source prerequisite: require real data before building a parser.

Explicit invocation: python -m pytest tests/test_socrates_live.py -v
These tests intentionally fail if the actual source cannot be accessed.
"""

import csv
import io
import subprocess

import pytest


def download_public_source(url: str) -> str:
    response = subprocess.run(
        ["curl", "--silent", "--show-error", "--fail-with-body",
         "--max-time", "30", url],
        capture_output=True, text=True, timeout=35,
    )
    assert response.returncode == 0, (
        f"Live source unavailable: {url}; curl exit {response.returncode}; "
        f"{response.stderr.strip()}"
    )
    assert response.stdout.strip(), f"Empty response: {url}"
    return response.stdout


@pytest.mark.live
def test_actual_socrates_format_documentation_accessible():
    content = download_public_source("https://celestrak.org/SOCRATES/socrates-format.php")
    assert "SOCRATES" in content.upper()


@pytest.mark.live
def test_actual_socrates_csv_download_is_nonempty():
    # Reuse the actual downloaded cache; repeated test runs must respect source policy.
    from app.config import settings
    from app.data.cache import FileCache
    from app.data.socrates import SOCRATES_URL, SocratesClient
    cache = FileCache(settings.cache_directory)
    dataset = SocratesClient(cache).get_dataset()
    assert dataset.data_status == "VALID"
    record = cache.read(SOCRATES_URL)
    assert record is not None
    content = record.payload
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    assert reader.fieldnames is not None
    assert {"NORAD_CAT_ID_1", "NORAD_CAT_ID_2", "TCA", "TCA_RANGE"} <= {
        field.strip() for field in reader.fieldnames
    }, f"Unexpected actual CSV headers: {reader.fieldnames}"
    rows = list(reader)
    print(f"Actual downloaded SOCRATES rows: {len(rows)}")
    assert rows, "No actual SOCRATES encounters downloaded"

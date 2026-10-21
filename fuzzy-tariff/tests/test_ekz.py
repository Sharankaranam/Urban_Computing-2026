import httpx
import pandas as pd
import pytest

from fuzzy_tariff.ingest.ekz import (
    EkzError,
    EkzTariffSource,
    parse_ekz_tariffs_json,
)

SAMPLE_JSON = {
    "publication_timestamp": "2026-10-20T17:50:30+02:00",
    "prices": [
        {
            "start_timestamp": "2026-10-21T00:00:00+02:00",
            "end_timestamp": "2026-10-21T00:15:00+02:00",
            "electricity": [{"unit": "CHF_m", "value": 3.0}, {"unit": "CHF_kWh", "value": 0.12020}],
            "grid": [{"unit": "CHF_m", "value": 0.0}, {"unit": "CHF_kWh", "value": 0.06245}],
            "integrated": [{"unit": "CHF_m", "value": 3.0}, {"unit": "CHF_kWh", "value": 0.18265}],
        },
        {
            "start_timestamp": "2026-10-21T00:15:00+02:00",
            "end_timestamp": "2026-10-21T00:30:00+02:00",
            "electricity": [{"unit": "CHF_m", "value": 3.0}, {"unit": "CHF_kWh", "value": 0.11947}],
            "grid": [{"unit": "CHF_m", "value": 0.0}, {"unit": "CHF_kWh", "value": 0.06245}],
            "integrated": [{"unit": "CHF_m", "value": 3.0}, {"unit": "CHF_kWh", "value": 0.18192}],
        },
    ],
}


def test_parse_ekz_tariffs_json():
    df = parse_ekz_tariffs_json(SAMPLE_JSON)
    assert len(df) == 2
    assert "total_rp" in df.columns
    assert "energy_rp" in df.columns
    assert "grid_rp" in df.columns
    assert "sdl_rp" in df.columns
    assert "price" in df.columns

    # Check first row values in Rp./kWh
    assert df.iloc[0]["energy_rp"] == pytest.approx(12.02, abs=0.01)
    assert df.iloc[0]["grid_rp"] == pytest.approx(6.245, abs=0.01)
    assert df.iloc[0]["total_rp"] == pytest.approx(18.265, abs=0.01)
    assert df.iloc[0]["price"] == pytest.approx(0.18265, abs=0.0001)

    # Check UTC index
    assert df.index.tz is not None
    assert str(df.index.tz) == "UTC"


def test_client_fetch_mocked():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "start_timestamp" in request.url.params
        assert "end_timestamp" in request.url.params
        return httpx.Response(200, json=SAMPLE_JSON)

    mock_client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    source = EkzTariffSource(client=mock_client)

    df = source.fetch("2026-10-21T00:00:00+02:00", "2026-10-21T01:00:00+02:00")
    assert len(df) == 2
    assert df.iloc[0]["total_rp"] == pytest.approx(18.265, abs=0.01)


def test_client_handles_error():
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    mock_client = httpx.Client(transport=httpx.MockTransport(error_handler))
    source = EkzTariffSource(client=mock_client)

    with pytest.raises(EkzError, match="status 500"):
        source.fetch("2026-10-21T00:00:00+02:00", "2026-10-21T01:00:00+02:00")

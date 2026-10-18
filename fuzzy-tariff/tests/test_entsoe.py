import pytest

from fuzzy_tariff.ingest.entsoe import EntsoeError, parse_day_ahead_xml

XML = """<?xml version="1.0" encoding="UTF-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
  <TimeSeries>
    <Period>
      <timeInterval><start>2025-01-01T23:00Z</start><end>2025-01-02T03:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><price.amount>80.5</price.amount></Point>
      <Point><position>2</position><price.amount>75.0</price.amount></Point>
      <Point><position>4</position><price.amount>90.0</price.amount></Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>"""

_ACK_NS = "urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:7:0"
ACK = f"""<Acknowledgement_MarketDocument xmlns="{_ACK_NS}">
  <Reason><code>999</code><text>No matching data found</text></Reason>
</Acknowledgement_MarketDocument>"""


def test_parses_points_and_forward_fills_omitted_positions():
    s = parse_day_ahead_xml(XML)
    assert len(s) == 4
    assert s.iloc[0] == 80.5 and s.iloc[1] == 75.0
    assert s.iloc[2] == 75.0  # position 3 omitted -> value repeats (curve type A03)
    assert s.iloc[3] == 90.0
    assert str(s.index.tz) == "UTC"


def test_acknowledgement_raises_with_reason():
    with pytest.raises(EntsoeError, match="No matching data"):
        parse_day_ahead_xml(ACK)


def test_client_builds_request_and_parses_response():
    import httpx

    from fuzzy_tariff.ingest.entsoe import EntsoeClient

    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, text=XML)

    client = EntsoeClient("tok", client=httpx.Client(transport=httpx.MockTransport(handler)))
    out = client.fetch_day_ahead(
        __import__("datetime").datetime(2025, 1, 1, 23),
        __import__("datetime").datetime(2025, 1, 2, 3),
    )
    assert seen["documentType"] == "A44" and seen["in_Domain"] == "10YCH-SWISSGRIDZ"
    assert seen["periodStart"] == "202501012300"
    assert len(out) == 4


def test_client_requires_token():
    from fuzzy_tariff.ingest.entsoe import EntsoeClient

    with pytest.raises(ValueError):
        EntsoeClient("")

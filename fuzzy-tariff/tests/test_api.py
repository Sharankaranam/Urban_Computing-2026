from fastapi.testclient import TestClient

from fuzzy_tariff.api.main import create_app

client = TestClient(create_app())


def test_health():
    assert client.get("/healthz").json()["status"] == "ok"


def test_score_returns_label_text_and_explanation():
    r = client.post("/v1/score", json={"P": 12, "A": 0.3, "G": 0.2, "lang": "de"})
    body = r.json()
    assert r.status_code == 200
    assert body["label"] == "ideal"
    assert body["text"] == "Sehr günstig: beste Zeit"
    assert body["fired_rules"][0]["id"] == "R01"


def test_score_validates_ranges():
    assert client.post("/v1/score", json={"P": 120, "A": 0.3}).status_code == 422


def test_advice_endpoint():
    r = client.post(
        "/v1/advice",
        json={"suitability": 15, "device": "ev", "energy_kwh": 70, "deadline_hours": 8},
    )
    assert r.status_code == 200 and r.json()["action"] == "must_start"


def test_plan_endpoint_and_error_path():
    ok = client.post(
        "/v1/plan",
        json={"scores": [10, 90, 20, 95], "device": "ev", "energy_kwh": 14.8},
    )
    assert ok.json()["slots"] == [1, 3]
    bad = client.post("/v1/plan", json={"scores": [10], "device": "ev", "energy_kwh": 50})
    assert bad.status_code == 422


def test_config_endpoint_exposes_rules():
    body = client.get("/v1/config").json()
    assert len(body["stage1"]["rules"]) == 15

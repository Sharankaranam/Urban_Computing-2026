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
    assert len(body["stage1"]["rules"]) == 19
    rule_ids = {r["id"] for r in body["stage1"]["rules"]}
    assert {"R16", "R17", "R18", "R19"}.issubset(rule_ids)


def test_edge_case_rules_fire():
    # R16: P low, T rising -> ideal (pre-spike surge)
    r16 = client.post("/v1/score", json={"P": 25, "A": 0.2, "G": 0.2, "T": 0.8}).json()
    assert "R16" in [f["id"] for f in r16["fired_rules"]]
    assert r16["label"] == "ideal"

    # R17: G high, A high -> avoid (emergency grid & cost ceiling)
    r17 = client.post("/v1/score", json={"P": 75, "A": 0.9, "G": 0.9, "T": 0.0}).json()
    assert "R17" in [f["id"] for f in r17["fired_rules"]]
    assert r17["label"] == "avoid"

    # R18: P low, T falling -> okay (trough anticipation)
    r18 = client.post("/v1/score", json={"P": 25, "A": 0.2, "G": 0.2, "T": -0.8}).json()
    assert "R18" in [f["id"] for f in r18["fired_rules"]]

    # R19: P high, A high -> avoid/suppressed score (double peak avoidance)
    r19 = client.post("/v1/score", json={"P": 75, "A": 0.9, "G": 0.5, "T": 0.0}).json()
    assert "R19" in [f["id"] for f in r19["fired_rules"]]
    assert r19["score"] < 25.0


def test_tariff_preview_practising_dataset():
    # Preview winter cold snap scenario (2026-12-15)
    res = client.get("/v1/tariff/preview", params={"season": "winter_cold_snap"}).json()
    assert res["date"] == "2026-12-15"
    assert len(res["steps"]) == 96
    # Verify steps have valid score and labels
    assert res["steps"][0]["score"] >= 0.0
    assert res["steps"][0]["label"] in {"ideal", "good", "okay", "wait", "avoid"}


def test_tariff_preview_dst_autumn():
    # Autumn DST scenario (2026-10-25)
    res = client.get("/v1/tariff/preview", params={"season": "autumn_dst"}).json()
    assert res["date"] == "2026-10-25"
    assert len(res["steps"]) >= 96


def test_smart_schedule_practising_dataset():
    payload = {
        "season": "winter_cold_snap",
        "max_concurrent_devices": 1,
        "max_total_kw": 11.0,
        "devices": [
            {
                "id": "ev",
                "name": "Electric Vehicle",
                "power_kw": 11.0,
                "energy_kwh": 22.0,
                "deadline_hours": 12.0,
                "contiguous": True,
            }
        ],
    }
    res = client.post("/v1/smart-schedule", json=payload).json()
    assert res["date"] == "2026-12-15"
    assert len(res["devices"]) == 1
    assert len(res["devices"][0]["slots"]) == 8  # 22 kWh / 11 kW = 2h = 8 steps of 15min
    assert res["total_savings_chf"] >= 0.0


def test_translate_endpoint():
    # Identity test
    res_id = client.post("/v1/translate", json={"text": "Hello", "source_lang": "en", "target_lang": "en"}).json()
    assert res_id["translated_text"] == "Hello"
    assert res_id["provider"] == "identity"

    # Translation test with live or fallback
    res_de = client.post("/v1/translate", json={"text": "Savings", "source_lang": "en", "target_lang": "de"}).json()
    assert res_de["translated_text"] != ""
    assert res_de["target_lang"] == "de"


def test_smart_schedule_multilingual_support():
    for lang in ["de", "fr", "it"]:
        payload = {
            "season": "winter",
            "max_concurrent_devices": 1,
            "lang": lang,
            "devices": [
                {
                    "id": "ev",
                    "name": "Electric Vehicle",
                    "power_kw": 7.4,
                    "energy_kwh": 22.2,
                    "deadline_hours": 10.0,
                    "contiguous": False,
                }
            ],
        }
        res = client.post("/v1/smart-schedule", json=payload).json()
        device_res = res["devices"][0]
        assert "advice_text" in device_res
        assert len(device_res["advice_text"]) > 0


def test_summarize_daily_endpoint():
    r = client.get("/v1/summarize/daily?season=winter&lang=en")
    assert r.status_code == 200
    data = r.json()
    assert "headline" in data
    assert len(data["headline"]) > 0
    assert len(data["narrative"]) == 4
    assert len(data["top_protoforms"]) > 0
    assert len(data["quantifiers"]) == 7
    assert len(data["qualifiers"]) == 8
    assert len(data["summarizers"]) == 9

    # Multilingual check
    r_de = client.get("/v1/summarize/daily?season=summer&lang=de")
    assert r_de.status_code == 200
    data_de = r_de.json()
    stmt = data_de["top_protoforms"][0]["statement"].lower()
    assert "intervalle" in stmt or "stunden" in stmt


def test_evaluate_protoform_endpoint_and_error():
    # Valid evaluation
    r = client.post(
        "/v1/summarize/evaluate",
        json={
            "season": "winter",
            "quantifier": "most",
            "qualifier": "night_hours",
            "summarizer": "ideal",
            "lang": "en",
        },
    )
    assert r.status_code == 200
    res = r.json()
    assert "truth_degree" in res
    assert 0.0 <= res["truth_degree"] <= 1.0
    assert res["status"] in ("valid", "moderate", "false")
    assert "Almost all" in res["statement"] or "Most" in res["statement"]

    # Invalid quantifier error path (422)
    bad = client.post(
        "/v1/summarize/evaluate",
        json={
            "season": "winter",
            "quantifier": "nonexistent_quantifier",
            "qualifier": "night_hours",
            "summarizer": "ideal",
        },
    )
    assert bad.status_code == 422




"""
Unit Tests for Week 3 Deliverables:
- FastAPI Backend REST Endpoints
- Forecast Bounds (Confidence Intervals) Verification
- PuLP Battery Arbitrage & SoC Gauge Payload Integrity
- React Production Build Static Serving
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.api.server import app, OptimizationRequest


@pytest.fixture
def client():
    return TestClient(app)


def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["milestone"] == "Week 3 MVP"
    assert 1 in data["plants_available"]


def test_api_plants(client):
    res = client.get("/api/plants")
    assert res.status_code == 200
    plants = res.json()
    assert len(plants) >= 2
    assert plants[0]["id"] == 1
    assert "rated_capacity_mw" in plants[0]


def test_api_overview(client):
    res = client.get("/api/overview?plant_id=1&granularity=hourly&limit=24")
    assert res.status_code == 200
    data = res.json()
    assert "kpis" in data
    assert "timeseries" in data
    assert data["kpis"]["total_energy_mwh"] > 0
    assert len(data["timeseries"]) > 0
    assert "ac_power_kw" in data["timeseries"][0]


def test_api_forecast_with_bounds(client):
    res = client.get("/api/forecast?plant_id=1&slice_length=24")
    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    assert "predictions" in data
    assert "bounds_info" in data
    assert "feature_importance" in data

    # Verify forecast bounds structure
    assert len(data["predictions"]) > 0
    first_pred = data["predictions"][0]
    assert "lightgbm" in first_pred
    assert "upper_bound" in first_pred
    assert "lower_bound" in first_pred
    # Upper bound must be >= lower bound
    for p in data["predictions"]:
        assert p["upper_bound"] >= p["lower_bound"]
        assert p["lower_bound"] >= 0.0, "Lower bound cannot be negative"


def test_api_optimization(client):
    payload = {
        "plant_id": 1,
        "battery_capacity_mwh": 10.0,
        "max_inverter_power_mw": 5.0,
        "round_trip_efficiency_pct": 90.25,
        "initial_soc_pct": 20.0,
        "off_peak_rate": 0.05,
        "normal_rate": 0.10,
        "peak_rate": 0.25,
        "export_feedin_rate": 0.04
    }
    res = client.post("/api/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert "kpis" in data
    assert "schedule" in data
    assert "financials" in data
    assert "soc_gauge" in data

    # Financial validation
    assert data["financials"]["daily_savings"] > 0
    assert data["financials"]["annual_savings_projected"] > 0
    assert data["financials"]["simple_payback_years"] > 0

    # SoC Gauge validation
    gauge = data["soc_gauge"]
    assert gauge["initial_soc_pct"] == 20.0
    assert gauge["safe_min_bound_pct"] == 10.0
    assert gauge["safe_max_bound_pct"] == 90.0
    assert gauge["terminal_condition_met"] is True

    # 24-hour schedule validation
    schedule = data["schedule"]
    assert len(schedule) == 24
    for row in schedule:
        assert 0 <= row["battery_soc_pct"] <= 100
        assert "tariff_tier" in row


def test_react_frontend_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Solar Grid Intelligence & BESS Optimization" in res.text


if __name__ == "__main__":
    test_client = TestClient(app)
    print("Running Week 3 API & UI tests...")
    test_api_status(test_client)
    print("✔ test_api_status passed.")
    test_api_plants(test_client)
    print("✔ test_api_plants passed.")
    test_api_overview(test_client)
    print("✔ test_api_overview passed.")
    test_api_forecast_with_bounds(test_client)
    print("✔ test_api_forecast_with_bounds passed.")
    test_api_optimization(test_client)
    print("✔ test_api_optimization passed.")
    test_react_frontend_served(test_client)
    print("✔ test_react_frontend_served passed.")
    print("All Week 3 unit tests passed successfully!")

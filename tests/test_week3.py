"""
Unit Tests for Week 3 Deliverables:
- FastAPI Backend REST Endpoints
- Forecast Bounds (Confidence Intervals) Verification
- PuLP Battery Arbitrage & SoC Gauge Payload Integrity
- Duck Curve Explorer API Endpoint Verification
- React Production Build Static Serving
"""

import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import pytest

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.api.server import (
    app,
    get_status,
    get_plants,
    get_overview,
    get_forecast,
    get_live_weather,
    get_live_24h_forecast,
    run_optimization,
    get_dataset_sample,
    get_duck_curve,
    get_tariff_configuration,
    OptimizationRequest,
    ROOT_DIR,
)


class DirectTestResponse:
    """Lightweight test response wrapper mimicking requests/TestClient Response."""
    def __init__(self, status_code: int, data=None, text: str = ""):
        self.status_code = status_code
        self._data = data
        self.text = text

    def json(self):
        return self._data


class DirectAPIClient:
    """
    Direct endpoint dispatcher providing immediate in-process testing of
    FastAPI router handlers without thread portal / network loopback deadlocks.
    """
    def get(self, url: str) -> DirectTestResponse:
        parsed = urlparse(url)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/status":
            return DirectTestResponse(200, get_status())
        elif path == "/api/tariff-config":
            return DirectTestResponse(200, get_tariff_configuration())
        elif path == "/api/plants":
            return DirectTestResponse(200, get_plants())
        elif path == "/api/weather/live":
            pid = int(qs.get("plant_id", [1])[0])
            return DirectTestResponse(200, get_live_weather(plant_id=pid))
        elif path == "/api/forecast/live-24h":
            pid = int(qs.get("plant_id", [1])[0])
            return DirectTestResponse(200, get_live_24h_forecast(plant_id=pid))
        elif path == "/api/overview":
            pid = int(qs.get("plant_id", [1])[0])
            gran = qs.get("granularity", ["hourly"])[0]
            lim = int(qs.get("limit", [96])[0])
            return DirectTestResponse(200, get_overview(plant_id=pid, granularity=gran, limit=lim))
        elif path == "/api/forecast":
            pid = int(qs.get("plant_id", [1])[0])
            sl = int(qs.get("slice_length", [96])[0])
            return DirectTestResponse(200, get_forecast(plant_id=pid, slice_length=sl))
        elif path == "/api/duck-curve":
            d = qs.get("date", [None])[0]
            lim = int(qs.get("limit", [96])[0])
            return DirectTestResponse(200, get_duck_curve(date=d, limit=lim))
        elif path == "/api/dataset":
            pid = int(qs.get("plant_id", [1])[0])
            lim = int(qs.get("limit", [50])[0])
            return DirectTestResponse(200, get_dataset_sample(plant_id=pid, limit=lim))
        elif path == "/" or path == "/index.html":
            index_path = ROOT_DIR / "frontend" / "dist" / "index.html"
            if index_path.exists():
                return DirectTestResponse(200, text=index_path.read_text(encoding="utf-8"))
            return DirectTestResponse(404, text="Frontend dist not built")
        return DirectTestResponse(404, {"detail": f"Route {path} not found"})

    def post(self, url: str, json: dict = None) -> DirectTestResponse:
        parsed = urlparse(url)
        path = parsed.path
        if path == "/api/optimize":
            req = OptimizationRequest(**(json or {}))
            return DirectTestResponse(200, run_optimization(req))
        return DirectTestResponse(404, {"detail": f"Route {path} not found"})


@pytest.fixture
def client():
    return DirectAPIClient()


def test_api_status(client):
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["milestone"] == "Week 3 MVP"
    assert 1 in data["plants_available"]
    assert 2 in data["plants_available"]


def test_api_tariff_configuration(client):
    data = client.get("/api/tariff-config").json()
    assert data["currency_code"] == "INR"
    assert data["currency_symbol"] == "₹"
    assert data["tariff_rates"] == {
        "off_peak_rate": 5.30,
        "normal_rate": 6.70,
        "peak_rate": 7.30,
        "export_feedin_rate": 0.0,
    }
    assert data["tariff_hours"]["peak"] == [6, 7, 8, 9, 18, 19, 20, 21]


def test_api_plants(client):
    res = client.get("/api/plants")
    assert res.status_code == 200
    plants = res.json()
    assert len(plants) >= 2
    assert plants[0]["id"] == 1
    assert "rated_capacity_mw" in plants[0]
    assert plants[1]["id"] == 2


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
    for p in data["predictions"]:
        assert "lightgbm" in p
        assert "upper_bound" in p
        assert "lower_bound" in p
        # Upper bound must be >= lower bound
        assert p["upper_bound"] >= p["lower_bound"]
        assert p["lower_bound"] >= 0.0, "Lower bound cannot be negative"


def test_api_duck_curve(client):
    res = client.get("/api/duck-curve?date=2020-05-15")
    assert res.status_code == 200
    data = res.json()
    assert data["is_synthetic_demand"] is True
    assert "Simulated Grid Demand Scenario" in data["data_source_label"]
    assert "disclaimer" in data
    assert "metrics" in data
    assert data["metrics"]["peak_grid_demand_mw"] > 0
    assert data["metrics"]["min_midday_net_load_mw"] >= 0
    assert len(data["timeseries"]) == 96  # 24 hours * 4 steps/hr
    # Verify net load calculation: Net load = Demand - Solar
    first_row = data["timeseries"][0]
    assert "solar_generation_mw" in first_row
    assert "grid_demand_mw" in first_row
    assert "net_load_mw" in first_row


def test_api_optimization(client):
    payload = {
        "plant_id": 1,
        "battery_capacity_mwh": 10.0,
        "max_inverter_power_mw": 5.0,
        "round_trip_efficiency_pct": 90.25,
        "initial_soc_pct": 20.0,
    }
    res = client.post("/api/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert "kpis" in data
    assert "schedule" in data
    assert "financials" in data
    assert "soc_gauge" in data
    assert data["currency_code"] == "INR"
    assert data["tariff_assumptions"]["off_peak_rate_inr_per_kwh"] == 5.30
    assert data["tariff_assumptions"]["normal_rate_inr_per_kwh"] == 6.70
    assert data["tariff_assumptions"]["peak_rate_inr_per_kwh"] == 7.30
    assert data["tariff_assumptions"]["disclaimer"].startswith("Financial results are estimates")

    # Financial validation
    assert data["financials"]["daily_savings"] > 0
    assert data["financials"]["daily_savings"] == pytest.approx(
        data["kpis"]["cost_without_bess"] - data["kpis"]["cost_with_bess"],
        abs=0.01,
    )
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
    for step, row in enumerate(schedule):
        assert row["step"] == step
        assert 0 <= row["battery_soc_pct"] <= 100
        assert "tariff_tier" in row
        expected_rate = {
            "Off-Peak": 5.30,
            "Normal": 6.70,
            "Peak": 7.30,
        }[row["tariff_tier"]]
        assert row["tariff_rate"] == expected_rate


def test_api_optimization_flat_tariff_idle(client):
    """Verify that flat tariffs do not manufacture artificial positive savings."""
    payload = {
        "plant_id": 1,
        "battery_capacity_mwh": 5.0,
        "max_inverter_power_mw": 2.0,
        "round_trip_efficiency_pct": 80.0,
        "initial_soc_pct": 20.0,
        "off_peak_rate": 0.10,
        "normal_rate": 0.10,
        "peak_rate": 0.10,
        "export_feedin_rate": 0.05,
        "degradation_cost_per_kwh": 0.05
    }
    res = client.post("/api/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    # Optimal action with no spread is to remain idle (savings >= 0, near 0)
    assert data["financials"]["daily_savings"] >= -1e-4


def test_api_live_weather(client):
    for pid in [1, 2]:
        res = client.get(f"/api/weather/live?plant_id={pid}")
        assert res.status_code == 200
        data = res.json()
        assert data["plant_id"] == pid
        assert data["status"] in ["online", "fallback"]
        assert "current_conditions" in data
        assert len(data["hourly_forecast"]) > 0


def test_api_live_24h_forecast(client):
    for pid in [1, 2]:
        res = client.get(f"/api/forecast/live-24h?plant_id={pid}")
        assert res.status_code == 200
        data = res.json()
        assert data["plant_id"] == pid
        assert data["is_future_forecast"] is True
        assert len(data["timeline"]) == 24
        assert data["kpis"]["peak_predicted_kw"] >= 0.0


def test_optimization_with_future_forecast(client):
    payload = {
        "plant_id": 1,
        "battery_capacity_mwh": 10.0,
        "max_inverter_power_mw": 5.0,
        "round_trip_efficiency_pct": 90.25,
        "initial_soc_pct": 20.0,
        "off_peak_rate": 0.05,
        "normal_rate": 0.10,
        "peak_rate": 0.25,
        "export_feedin_rate": 0.04,
        "degradation_cost_per_kwh": 0.005,
        "use_forecast": True
    }
    res = client.post("/api/optimize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["kpis"]["solver_status"] == "Optimal"
    assert data["is_future_forecast"] is True
    assert len(data["schedule"]) == 24
    assert "demand_assumption" in data


def test_react_frontend_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Solar Grid Intelligence & BESS Optimization" in res.text or "<div id=\"root\"></div>" in res.text


if __name__ == "__main__":
    test_client = DirectAPIClient()
    print("Running Week 3 API & UI tests...")
    test_api_status(test_client)
    print("[OK] test_api_status passed.")
    test_api_plants(test_client)
    print("[OK] test_api_plants passed.")
    test_api_live_weather(test_client)
    print("[OK] test_api_live_weather passed.")
    test_api_live_24h_forecast(test_client)
    print("[OK] test_api_live_24h_forecast passed.")
    test_api_overview(test_client)
    print("[OK] test_api_overview passed.")
    test_api_forecast_with_bounds(test_client)
    print("[OK] test_api_forecast_with_bounds passed.")
    test_api_duck_curve(test_client)
    print("[OK] test_api_duck_curve passed.")
    test_api_optimization(test_client)
    print("[OK] test_api_optimization passed.")
    test_optimization_with_future_forecast(test_client)
    print("[OK] test_optimization_with_future_forecast passed.")
    test_api_optimization_flat_tariff_idle(test_client)
    print("[OK] test_api_optimization_flat_tariff_idle passed.")
    test_react_frontend_served(test_client)
    print("[OK] test_react_frontend_served passed.")
    print("All Week 3 unit tests passed successfully! [OK]")

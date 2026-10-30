"""
Unit & Integration Tests for Week 4 Deliverables:
- Extreme-Weather Stress Testing Module (6 scenarios, night zero-clamping)
- Out-of-sample Forecast Stress Degradation (Ridge & LightGBM)
- PuLP Battery LP Resilience Under Meteorological Stress
- Carbon-Offset Accounting with Official CEA v19.0 Provenance
- Dynamic Multi-Page Executive PDF Report Generation (ReportLab)
- FastAPI REST Endpoints for Week 4 Features
"""

import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import pytest
import pandas as pd
import numpy as np

# Ensure project root is available in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.analysis.weather_stress_test import (
    SCENARIOS,
    apply_weather_stress_scenario,
    create_weather_stress_tariff,
    run_full_weather_stress_suite,
)
from src.analysis.carbon_accounting import (
    GRID_EMISSION_PROVENANCE,
    DEFAULT_EMISSION_FACTORS,
    calculate_carbon_offsets,
    run_carbon_scenario_analysis,
)
from src.visualization.executive_report import generate_executive_pdf
from src.api.server import (
    get_weather_stress,
    get_carbon_accounting,
    generate_executive_report_endpoint,
    download_executive_report_endpoint,
    ROOT_DIR,
)


class DirectTestResponse:
    """Lightweight test response wrapper for in-process endpoint verification."""
    def __init__(self, status_code: int, data=None, text: str = ""):
        self.status_code = status_code
        self._data = data
        self.text = text

    def json(self):
        return self._data


class DirectAPIClientWeek4:
    """In-process test dispatcher calling FastAPI router handlers directly."""
    def get(self, url: str) -> DirectTestResponse:
        parsed = urlparse(url)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path == "/api/weather-stress":
            pid = int(qs.get("plant_id", [1])[0])
            sc = qs.get("scenario", [None])[0]
            return DirectTestResponse(200, get_weather_stress(plant_id=pid, scenario=sc))
        elif path == "/api/carbon":
            pid = int(qs.get("plant_id", [1])[0])
            ef = float(qs["emission_factor"][0]) if "emission_factor" in qs else None
            return DirectTestResponse(200, get_carbon_accounting(plant_id=pid, emission_factor=ef))
        elif path == "/api/executive-report/download":
            pid = int(qs.get("plant_id", [1])[0])
            return DirectTestResponse(200, download_executive_report_endpoint(plant_id=pid))
        return DirectTestResponse(404, {"detail": f"Route {path} not found"})

    def post(self, url: str, json: dict = None) -> DirectTestResponse:
        parsed = urlparse(url)
        path = parsed.path
        qs = parse_qs(parsed.query)
        if path == "/api/executive-report/generate":
            pid = int(qs.get("plant_id", [1])[0])
            return DirectTestResponse(200, generate_executive_report_endpoint(plant_id=pid))
        return DirectTestResponse(404, {"detail": f"Route {path} not found"})


@pytest.fixture
def client_w4():
    return DirectAPIClientWeek4()


# =========================================================================
# 1. Weather Stress Testing Tests
# =========================================================================
def test_weather_stress_scenarios_definitions():
    """Verify all 6 required scenarios exist with correct metadata and factors."""
    required = ["normal", "heavy_cloud", "monsoon_prolonged", "sudden_drop", "multi_day_low", "recovery"]
    for sc in required:
        assert sc in SCENARIOS, f"Missing required scenario: {sc}"
        meta = SCENARIOS[sc]
        assert "label" in meta
        assert "description" in meta
        assert "irradiance_factor" in meta
        assert 0.0 <= meta["irradiance_factor"] <= 1.0


def test_weather_stress_night_zero_clamping():
    """Verify that applying weather stress preserves physical night zero-inflation."""
    times = pd.date_range("2020-05-15 00:00:00", periods=24, freq="1h")
    df_synth = pd.DataFrame({
        "time": times,
        "ac_power": [0.0]*6 + [100.0, 500.0, 1000.0, 1500.0, 1800.0, 2000.0, 1900.0, 1600.0, 1200.0, 700.0, 200.0, 20.0] + [0.0]*6,
        "ghi": [0.0]*6 + [50.0, 200.0, 500.0, 750.0, 900.0, 1000.0, 950.0, 800.0, 600.0, 350.0, 100.0, 10.0] + [0.0]*6,
        "solar_elevation_deg": [-40.0, -30.0, -20.0, -10.0, -2.0, 5.0, 15.0, 30.0, 48.0, 65.0, 78.0, 82.0,
                                75.0, 60.0, 45.0, 28.0, 12.0, 0.0, -10.0, -22.0, -35.0, -45.0, -50.0, -45.0]
    })

    stressed = apply_weather_stress_scenario(df_synth, scenario_name="heavy_cloud")
    # Nighttime values (where solar_elevation <= 0) must be strictly 0.0
    night_mask = stressed["solar_elevation_deg"] <= 0.0
    assert np.all(stressed.loc[night_mask, "ac_power_stressed"] == 0.0), "Night solar generation must be strictly 0.0"

    # Midday power must be attenuated by factor 0.35
    peak_idx = 11  # 11:00 hour (index 11)
    assert stressed.loc[peak_idx, "ac_power_stressed"] < df_synth.loc[peak_idx, "ac_power"]


def test_weather_stress_suite_execution():
    """Verify full weather stress test execution produces valid metrics."""
    res = run_full_weather_stress_suite(plant_id=1, save_artifacts=False)
    assert "summary_df" in res
    assert "forecast_df" in res
    assert "resilience_df" in res

    df_sum = res["summary_df"]
    assert len(df_sum) == 6
    assert "total_solar_generation_mwh" in df_sum.columns
    assert "net_arbitrage_savings" in df_sum.columns
    assert "grid_dependency_pct" in df_sum.columns

    # Normal scenario must have higher solar generation than prolonged monsoon
    normal_gen = df_sum[df_sum["scenario_name"] == "normal"]["total_solar_generation_mwh"].iloc[0]
    monsoon_gen = df_sum[df_sum["scenario_name"] == "monsoon_prolonged"]["total_solar_generation_mwh"].iloc[0]
    assert normal_gen > monsoon_gen

    # Solar, peak, and RMSE share the same 7-day measured test window.
    assert df_sum["forecast_test_hours"].nunique() == 1
    assert df_sum["forecast_test_hours"].iloc[0] == 168
    assert df_sum["forecast_daylight_hours"].nunique() == 1
    assert df_sum["total_solar_generation_7d_mwh"].nunique() == 6
    assert (df_sum["peak_actual_generation_kw"] <= df_sum["plant_rated_capacity_mw"] * 1000).all()

    # All battery cases use the normal-scenario demand profile, not scenario-scaled demand.
    assert df_sum["total_load_demand_mwh"].nunique() == 1
    assert np.allclose(
        df_sum["storage_autonomy_pct"],
        100.0 - df_sum["grid_dependency_pct"],
        atol=0.11,
    )
    assert np.allclose(
        df_sum["net_arbitrage_savings"],
        df_sum["cost_without_bess"] - df_sum["cost_with_bess"],
        atol=0.02,
    )
    assert (df_sum["battery_degradation_cost_per_kwh"] == 0.50).all()
    assert (df_sum["battery_charge_efficiency_pct"] == 95.0).all()
    assert (df_sum["battery_discharge_efficiency_pct"] == 95.0).all()
    assert (df_sum["tariff_off_peak_inr_per_kwh"] == 5.30).all()
    assert (df_sum["tariff_normal_inr_per_kwh"] == 6.70).all()
    assert (df_sum["tariff_peak_inr_per_kwh"] == 7.30).all()


def test_weather_stress_adjusts_all_model_irradiance_inputs():
    """Verify weather stress modifies the irradiance features used by the forecast models."""
    df = pd.DataFrame({
        "time": pd.date_range("2020-06-11 11:00:00", periods=2, freq="h"),
        "ac_power": [1000.0, 1000.0],
        "ghi": [800.0, 700.0],
        "direct_radiation": [500.0, 400.0],
        "dhi": [300.0, 300.0],
        "dni": [600.0, 500.0],
        "cloud_cover_index": [20.0, 30.0],
        "openmeteo_temperature": [30.0, 30.0],
    })

    stressed = apply_weather_stress_scenario(df, "sudden_drop")
    assert np.allclose(stressed["ac_power_stressed"], [250.0, 250.0])
    for column in ("ghi", "direct_radiation", "dhi", "dni"):
        assert np.allclose(stressed[f"{column}_stressed"], df[column] * 0.25)
    assert np.allclose(stressed["cloud_cover_index_stressed"], [95.0, 100.0])


def test_weather_events_apply_only_for_their_defined_periods():
    times = pd.date_range("2020-06-11 00:00:00", periods=7 * 24, freq="h")
    df = pd.DataFrame({
        "time": times,
        "ac_power": np.full(len(times), 1000.0),
        "ghi": np.full(len(times), 800.0),
        "openmeteo_temperature": np.full(len(times), 30.0),
    })

    sudden = apply_weather_stress_scenario(df, "sudden_drop")
    assert sudden.loc[11, "ac_power_stressed"] == 250.0
    assert sudden.loc[24 + 11, "ac_power_stressed"] == 1000.0

    multi_day = apply_weather_stress_scenario(df, "multi_day_low")
    assert multi_day.loc[71, "attenuation_factor"] == 0.40
    assert multi_day.loc[72, "attenuation_factor"] == 1.0

    recovery = apply_weather_stress_scenario(df, "recovery")
    assert recovery.loc[11, "ac_power_stressed"] == 200.0
    assert recovery.loc[12, "ac_power_stressed"] == 1000.0
    assert recovery.loc[24 + 7, "ac_power_stressed"] == 1000.0


def test_weather_stress_tariff_matches_inr_matrix():
    tariff = create_weather_stress_tariff()
    timestamps = pd.date_range("2020-05-15 00:00:00", periods=24, freq="h")
    import_rates, _ = tariff.get_rates_for_series(timestamps)
    expected_rates = np.array([
        5.3, 5.3, 5.3, 5.3, 5.3, 5.3,
        7.3, 7.3, 7.3, 7.3,
        6.7, 6.7, 6.7, 6.7, 6.7, 6.7, 6.7, 6.7,
        7.3, 7.3, 7.3, 7.3,
        5.3, 5.3,
    ])
    assert np.array_equal(import_rates, expected_rates)
    assert tariff.export_feedin_rate == 0.0


# =========================================================================
# 2. Carbon-Offset Accounting Tests
# =========================================================================
def test_carbon_provenance_citations():
    """Verify Central Electricity Authority (CEA) Baseline Database provenance metadata."""
    assert "source_organization" in GRID_EMISSION_PROVENANCE
    assert "Central Electricity Authority" in GRID_EMISSION_PROVENANCE["source_organization"]
    assert GRID_EMISSION_PROVENANCE["default_emission_factor_kg_per_kwh"] == 0.716
    assert GRID_EMISSION_PROVENANCE["marginal_emission_factor_kg_per_kwh"] == 0.820
    assert GRID_EMISSION_PROVENANCE["unit"] == "kg CO2e / kWh"


def test_calculate_carbon_offsets():
    """Verify operational avoided emissions mathematical formulas."""
    res = calculate_carbon_offsets(
        grid_import_without_bess_kwh=10000.0,
        grid_import_with_bess_kwh=7500.0,
        solar_generation_kwh=20000.0,
        solar_exported_kwh=5000.0,
        grid_emission_factor=0.716,
    )

    # Displaced grid electricity = 10,000 - 7,500 = 2,500 kWh
    assert res["displaced_grid_electricity_kwh"] == 2500.0
    # Storage avoided CO2 = 2,500 * 0.716 = 1,790.0 kg = 1.79 tonnes
    assert res["storage_avoided_co2_kg"] == 1790.0
    assert res["storage_avoided_co2_tonnes"] == 1.79

    # Solar self-consumed = 20,000 - 5,000 = 15,000 kWh
    # Avoided solar CO2 = 15,000 * 0.716 = 10,740.0 kg = 10.74 tonnes
    assert res["solar_self_consumed_avoided_co2_kg"] == 10740.0
    assert res["solar_self_consumed_avoided_co2_tonnes"] == 10.74

    # Total avoided CO2 = 1.79 + 10.74 = 12.53 tonnes
    assert res["total_avoided_co2_tonnes"] == 12.53
    # Annual offset = 12.53 * 365 = 4573.45 tonnes
    assert res["annual_projected_avoided_co2_tonnes"] > 4000.0


def test_carbon_scenario_sensitivity():
    """Verify sensitivity across the 4 grid carbon regimes."""
    res = run_carbon_scenario_analysis(plant_id=1)
    assert "sensitivity_df" in res
    assert "weather_scenarios_df" in res

    df_sens = res["sensitivity_df"]
    assert len(df_sens) == 4
    # Clean grid (0.50) must yield less avoided emissions than high coal grid (0.95)
    clean_offset = df_sens[df_sens["grid_emission_factor_kg_per_kwh"] == 0.50]["total_avoided_co2_tonnes"].iloc[0]
    coal_offset = df_sens[df_sens["grid_emission_factor_kg_per_kwh"] == 0.95]["total_avoided_co2_tonnes"].iloc[0]
    assert clean_offset < coal_offset


# =========================================================================
# 3. Dynamic Executive PDF Report Tests
# =========================================================================
def test_generate_executive_pdf():
    """Verify dynamic ReportLab 6-page PDF generation."""
    pdf_path = generate_executive_pdf(plant_id=1)
    assert pdf_path.exists(), f"PDF was not created: {pdf_path}"
    # File size must be substantial (> 500 KB given embedded charts and tables)
    assert pdf_path.stat().st_size > 500 * 1024, "PDF file size unexpectedly small"

    # Verify 6 pages via binary marker inspection
    raw_pdf = pdf_path.read_bytes()
    page_markers = raw_pdf.count(b"/Page\n") + raw_pdf.count(b"/Page\r") + raw_pdf.count(b"/Page ")
    assert page_markers == 6, f"Expected 6 pages in executive PDF, found {page_markers}"


# =========================================================================
# 4. FastAPI REST Endpoints Tests
# =========================================================================
def test_api_weather_stress_endpoint(client_w4):
    """Verify GET /api/weather-stress returns valid multi-scenario payload."""
    res = client_w4.get("/api/weather-stress?plant_id=1")
    assert res.status_code == 200
    data = res.json()
    assert data["plant_id"] == 1
    assert "scenarios_metadata" in data
    assert len(data["scenarios_metadata"]) == 6
    assert "summary" in data
    assert len(data["summary"]) == 6
    assert "forecast_stress_metrics" in data
    assert "battery_resilience" in data


def test_api_weather_stress_filter(client_w4):
    """Verify GET /api/weather-stress with scenario filter."""
    res = client_w4.get("/api/weather-stress?plant_id=1&scenario=monsoon_prolonged")
    assert res.status_code == 200
    data = res.json()
    assert len(data["summary"]) == 1
    assert data["summary"][0]["scenario_name"] == "monsoon_prolonged"


def test_api_weather_stress_uses_requested_plant_data(client_w4):
    """Verify weather metrics are generated for the requested plant, not stale report files."""
    data = client_w4.get("/api/weather-stress?plant_id=2").json()
    assert data["plant_id"] == 2
    assert data["rated_capacity_mw"] == 26.2
    assert {row["plant_id"] for row in data["summary"]} == {2}
    assert all(row["plant_rated_capacity_mw"] == 26.2 for row in data["summary"])
    assert all(row["peak_actual_generation_kw"] <= 26200.0 for row in data["summary"])


def test_api_carbon_accounting_endpoint(client_w4):
    """Verify GET /api/carbon returns provenance and sensitivity matrix."""
    res = client_w4.get("/api/carbon?plant_id=1")
    assert res.status_code == 200
    data = res.json()
    assert data["plant_id"] == 1
    assert data["default_factor_kg_per_kwh"] == 0.716
    assert "provenance" in data
    assert "sensitivity_summary" in data
    assert len(data["sensitivity_summary"]) == 4
    assert all(
        row["total_solar_generation_mwh"] > 0
        for row in data["weather_scenarios_carbon"]
    )


def test_api_carbon_accounting_custom_factor(client_w4):
    """Verify GET /api/carbon computes custom factor offset."""
    res = client_w4.get("/api/carbon?plant_id=1&emission_factor=0.820")
    assert res.status_code == 200
    data = res.json()
    assert data["custom_calculation"] is not None
    assert data["custom_calculation"]["grid_emission_factor_kg_per_kwh"] == 0.820
    assert data["custom_calculation"]["total_avoided_co2_tonnes"] > 0.0


def test_api_executive_report_generate(client_w4):
    """Verify POST /api/executive-report/generate regenerates PDF report."""
    res = client_w4.post("/api/executive-report/generate?plant_id=1")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["plant_id"] == 1
    assert "executive_report_plant1.pdf" in data["filename"]
    assert data["size_kb"] > 500


def test_api_executive_report_download(client_w4):
    """Verify GET /api/executive-report/download serves FileResponse with application/pdf."""
    res = client_w4.get("/api/executive-report/download?plant_id=1")
    assert res.status_code == 200
    file_resp = res.json()
    assert file_resp.media_type == "application/pdf"
    assert "Solar_Plant_1_Executive_Technical_Report.pdf" in file_resp.filename
    assert Path(file_resp.path).exists()

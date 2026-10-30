"""
Unit Tests for Week 2 AI/ML Deliverables:
- LightGBM Solar Forecaster
- Facebook Prophet Forecaster
- PuLP Linear Programming Battery Arbitrage Optimizer
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.models.forecasting import (
    LightGBMForecaster,
    ProphetForecaster,
    XGBoostForecaster,
    generate_24h_ahead_solar_forecast,
)
from src.optimization.battery_lp import BatterySpecs, TOUTariff, BatteryOptimizerLP


def get_sample_solar_df():
    """Generates synthetic 48-hour solar dataframe."""
    timestamps = pd.date_range("2020-05-15 00:00:00", periods=48, freq="h")
    hours = timestamps.hour.values
    solar_profile = np.maximum(0.0, np.sin((hours - 6) * np.pi / 12) * 500.0)
    solar_profile[(hours < 6) | (hours > 18)] = 0.0

    df = pd.DataFrame({
        "time": timestamps,
        "ac_power": solar_profile,
        "ghi": solar_profile * 1.5,
        "openmeteo_temperature": 25.0 + 8.0 * np.sin((hours - 8) * np.pi / 12),
        "cos_zenith": np.maximum(0.0, np.sin((hours - 6) * np.pi / 12)),
        "solar_elevation_deg": np.maximum(-10.0, 60.0 * np.sin((hours - 6) * np.pi / 12)),
        "hour_sin": np.sin(2 * np.pi * hours / 24.0),
        "hour_cos": np.cos(2 * np.pi * hours / 24.0),
        "ac_power_lag_1h": np.roll(solar_profile, 1),
        "ac_power_lag_24h": np.roll(solar_profile, 24),
    })
    return df


def test_lightgbm_forecaster():
    print("Testing LightGBM Forecaster...")
    sample_solar_df = get_sample_solar_df()
    train_df = sample_solar_df.iloc[:36].copy()
    test_df = sample_solar_df.iloc[36:].copy()

    forecaster = LightGBMForecaster(
        feature_cols=["ghi", "openmeteo_temperature", "cos_zenith", "hour_sin", "hour_cos"],
        target_col="ac_power",
        n_estimators=50,
    )
    forecaster.fit(train_df)
    assert forecaster.is_fitted, "Forecaster should be fitted"

    preds = forecaster.predict(test_df, enforce_night_zero=True)
    assert len(preds) == len(test_df), f"Expected {len(test_df)} predictions, got {len(preds)}"
    assert np.all(preds >= 0.0), "Predictions must not be negative"

    # Nighttime zero-inflation check
    night_indices = np.where(test_df["cos_zenith"] <= 0)[0]
    if len(night_indices) > 0:
        assert np.all(preds[night_indices] == 0.0), "Nighttime predictions must be zero"
    print("[OK] LightGBM forecaster passed.")


def test_xgboost_forecaster():
    print("Testing XGBoost Forecaster...")
    sample_solar_df = get_sample_solar_df()
    train_df = sample_solar_df.iloc[:36].copy()
    test_df = sample_solar_df.iloc[36:].copy()

    forecaster = XGBoostForecaster(
        feature_cols=["ghi", "openmeteo_temperature", "cos_zenith", "hour_sin", "hour_cos"],
        target_col="ac_power",
        n_estimators=50,
        max_depth=4,
    )
    forecaster.fit(train_df)
    assert forecaster.is_fitted, "XGBoost forecaster should be fitted"

    preds = forecaster.predict(test_df, enforce_night_zero=True)
    assert len(preds) == len(test_df), f"Expected {len(test_df)} predictions, got {len(preds)}"
    assert np.all(preds >= 0.0), "Predictions must not be negative"

    # Nighttime zero-inflation check
    night_indices = np.where(test_df["cos_zenith"] <= 0)[0]
    if len(night_indices) > 0:
        assert np.all(preds[night_indices] == 0.0), "Nighttime predictions must be zero"
    print("[OK] XGBoost forecaster passed.")


def test_genuine_24h_ahead_solar_forecast():
    print("Testing Genuine 24-Hour Ahead Solar Forecast...")
    for pid in [1, 2]:
        res = generate_24h_ahead_solar_forecast(plant_id=pid, horizon_hours=24)
        assert res["status"] == "success"
        assert res["is_future_forecast"] is True
        assert len(res["timeline"]) == 24
        assert res["kpis"]["peak_predicted_kw"] >= 0.0
        assert "LightGBM" in res["model_champion"]
        # Check non-negative and nighttime zero
        for step in res["timeline"]:
            assert step["selected_solar_kw"] >= 0.0
            if not step["is_daylight"]:
                assert step["selected_solar_kw"] == 0.0
    print("[OK] Genuine 24-hour ahead solar forecast passed.")



def test_prophet_forecaster():
    print("Testing Prophet Forecaster...")
    sample_solar_df = get_sample_solar_df()
    train_df = sample_solar_df.iloc[:36].copy()
    test_df = sample_solar_df.iloc[36:].copy()

    forecaster = ProphetForecaster(
        time_col="time",
        target_col="ac_power",
        regressors=["ghi", "openmeteo_temperature", "cos_zenith"],
    )
    try:
        forecaster.fit(train_df)
    except RuntimeError as e:
        if "WinError 623" in str(e) or "System DLL Relocation" in str(e) or "DLL" in str(e):
            import pytest
            pytest.skip(f"Prophet Stan binary unavailable on Windows Python 3.13 due to DLL relocation conflict: {e}")
        raise

    assert forecaster.model is not None, "Prophet model should be initialized"

    preds = forecaster.predict(test_df, enforce_night_zero=True)
    assert len(preds) == len(test_df), f"Expected {len(test_df)} predictions, got {len(preds)}"
    assert np.all(preds >= 0.0), "Predictions must not be negative"
    print("[OK] Prophet forecaster passed.")


def test_pulp_battery_optimization():
    print("Testing PuLP Battery Optimization...")
    solar = np.array([0]*6 + [100, 300, 700, 1000, 1200, 1200, 1000, 700, 300, 50] + [0]*8, dtype=float)
    load = np.full(24, 400.0, dtype=float)

    specs = BatterySpecs(
        capacity_kwh=1000.0,
        max_charge_kw=500.0,
        max_discharge_kw=500.0,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        soc_min=0.10,
        soc_max=0.90,
        soc_initial=0.20,
    )
    tariff = TOUTariff(off_peak_rate=0.05, normal_rate=0.10, peak_rate=0.25)
    optimizer = BatteryOptimizerLP(specs=specs, tariff=tariff)

    res = optimizer.optimize_dispatch(solar_kw=solar, load_kw=load, dt_hours=1.0)
    assert res["solver_status"] == "Optimal", f"Solver status should be Optimal, got {res['solver_status']}"

    schedule = res["schedule_df"]
    assert len(schedule) == 24, "Schedule length must match horizon 24"
    assert np.all(schedule["battery_soc_pct"] >= specs.soc_min * 100.0 - 1e-4), "SoC dropped below minimum"
    assert np.all(schedule["battery_soc_pct"] <= specs.soc_max * 100.0 + 1e-4), "SoC exceeded maximum"

    expected_unmanaged_import = np.maximum(load - solar, 0.0)
    assert np.allclose(
        schedule["grid_import_unmanaged_kw"],
        expected_unmanaged_import,
        atol=0.05,
    ), "Grid imports without battery must equal demand minus solar generation"

    grid_balance = (
        schedule["solar_generation_kw"]
        + schedule["battery_discharge_kw"]
        + schedule["grid_import_with_bess_kw"]
        - schedule["load_demand_kw"]
        - schedule["battery_charge_kw"]
        - schedule["grid_export_with_bess_kw"]
    )
    assert np.allclose(grid_balance, 0.0, atol=0.05), "Hourly grid imports must satisfy the power balance"

    # Mutual exclusivity: battery cannot simultaneously charge and discharge
    simultaneous = (schedule["battery_charge_kw"] > 1e-3) & (schedule["battery_discharge_kw"] > 1e-3)
    assert not np.any(simultaneous), "Battery cannot simultaneously charge and discharge"

    kpis = res["kpi_summary"]
    assert kpis["cost_with_bess"] <= kpis["cost_without_bess"], "BESS cost should be <= baseline"
    assert kpis["net_arbitrage_savings"] >= 0.0, "Arbitrage savings should be non-negative in profitable spread"
    print("[OK] PuLP battery optimization passed.")


def test_synthetic_demand_uses_forecast_clock_hours():
    solar = np.full(24, 1000.0)
    timestamps = pd.date_range("2026-10-29 13:00:00", periods=24, freq="h")
    optimizer = BatteryOptimizerLP()

    res = optimizer.optimize_dispatch(
        solar_kw=solar,
        timestamps=timestamps,
        dt_hours=1.0,
    )

    hours = timestamps.hour.to_numpy()
    expected_load = (
        0.5
        + 0.2 * np.sin((hours - 8) * np.pi / 12)
        + 0.4 * np.exp(-((hours - 19) ** 2) / 8.0)
    ) * 1000.0 * 0.85

    assert res["solver_status"] == "Optimal"
    assert np.allclose(
        res["schedule_df"]["load_demand_kw"],
        expected_load,
        atol=0.01,
    ), "Synthetic demand must follow each forecast timestamp's clock hour"


def test_battery_negative_savings_handling():
    """Verify that when round-trip losses and degradation exceed flat tariff spread, negative savings are handled properly."""
    solar = np.zeros(24, dtype=float)
    load = np.full(24, 100.0, dtype=float)
    # Flat tariff with zero spread means cycling would only lose energy and incur degradation
    specs = BatterySpecs(
        capacity_kwh=500.0,
        max_charge_kw=200.0,
        max_discharge_kw=200.0,
        charge_efficiency=0.85,
        discharge_efficiency=0.85,
        soc_min=0.10,
        soc_max=0.90,
        soc_initial=0.20,
        degradation_cost_per_kwh=0.05,
    )
    tariff = TOUTariff(off_peak_rate=0.10, normal_rate=0.10, peak_rate=0.10, export_feedin_rate=0.05)
    optimizer = BatteryOptimizerLP(specs=specs, tariff=tariff)
    res = optimizer.optimize_dispatch(solar_kw=solar, load_kw=load, dt_hours=1.0)
    assert res["solver_status"] == "Optimal"
    kpis = res["kpi_summary"]
    # With a flat rate, optimal strategy is to stay idle (0 cycling), resulting in 0 net savings rather than artificial forced positive
    assert kpis["net_arbitrage_savings"] >= -1e-4
    print("[OK] Flat tariff & degradation handling passed.")


if __name__ == "__main__":
    print("=" * 60)
    print("[INFO] RUNNING WEEK 2 UNIT TESTS")
    print("=" * 60)
    test_lightgbm_forecaster()
    test_xgboost_forecaster()
    test_genuine_24h_ahead_solar_forecast()
    test_pulp_battery_optimization()
    test_synthetic_demand_uses_forecast_clock_hours()
    test_battery_negative_savings_handling()
    print("=" * 60)
    print("ALL WEEK 2 LP & FORECASTER TESTS PASSED SUCCESSFULLY! [OK]")
    print("=" * 60)

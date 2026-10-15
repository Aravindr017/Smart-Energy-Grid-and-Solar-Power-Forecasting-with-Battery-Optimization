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

from src.models.forecasting import LightGBMForecaster, ProphetForecaster
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
    print("✔ LightGBM forecaster passed.")


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
    forecaster.fit(train_df)
    assert forecaster.model is not None, "Prophet model should be initialized"

    preds = forecaster.predict(test_df, enforce_night_zero=True)
    assert len(preds) == len(test_df), f"Expected {len(test_df)} predictions, got {len(preds)}"
    assert np.all(preds >= 0.0), "Predictions must not be negative"
    print("✔ Prophet forecaster passed.")


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

    kpis = res["kpi_summary"]
    assert kpis["cost_with_bess"] <= kpis["cost_without_bess"], "BESS cost should be <= baseline"
    assert kpis["net_arbitrage_savings"] >= 0.0, "Arbitrage savings should be non-negative"
    print("✔ PuLP battery optimization passed.")


if __name__ == "__main__":
    print("=" * 60)
    print("⚡ RUNNING WEEK 2 UNIT TESTS")
    print("=" * 60)
    test_lightgbm_forecaster()
    test_prophet_forecaster()
    test_pulp_battery_optimization()
    print("=" * 60)
    print("ALL WEEK 2 TESTS PASSED SUCCESSFULLY! ✔")
    print("=" * 60)

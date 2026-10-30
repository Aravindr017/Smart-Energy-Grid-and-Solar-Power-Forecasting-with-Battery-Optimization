"""
Extreme-Weather Stress-Testing Module (Week 4 Deliverable)
Simulates and evaluates solar forecasting and battery resilience under:
1. Normal Operating Conditions
2. Heavy Cloud Cover
3. Monsoon / Prolonged Low-Irradiance
4. Sudden Irradiance Reduction (Convective Storm Transient)
5. Multi-Day Low-Solar Generation
6. Rapid Post-Storm Irradiance Recovery

Includes:
- Weather scenario generator preserving physical night zero-inflation
- Out-of-sample forecast stress evaluation (Ridge & LightGBM)
- PuLP Battery LP resilience stress testing (grid dependence, autonomy, throughput)
- Automated report and publication figure generation
"""

import os
import sys
import tempfile
from pathlib import Path

# Ensure project root is available in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

# Headless matplotlib configuration
os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.data.loader import load_processed_handoff, get_project_root
from src.features.engineering import apply_nighttime_zero_inflation
from src.models.baseline import temporal_train_test_split, LinearBaselinePipeline
from src.models.forecasting import LightGBMForecaster
from src.models.metrics import evaluate_forecast
from src.optimization.battery_lp import (
    BatterySpecs,
    TOUTariff,
    BatteryOptimizerLP,
    create_synthetic_load_profile,
)

ROOT_DIR = get_project_root()
PLANT_RATED_CAPACITY_MW = {1: 29.5, 2: 26.2}


def create_weather_stress_tariff() -> TOUTariff:
    """Build the INR tariff represented in the Week 2 tariff matrix."""
    return TOUTariff(
        off_peak_rate=5.30,
        normal_rate=6.70,
        peak_rate=7.30,
        export_feedin_rate=0.0,
        off_peak_hours=(22, 23, 0, 1, 2, 3, 4, 5),
        normal_hours=(10, 11, 12, 13, 14, 15, 16, 17),
        peak_hours=(6, 7, 8, 9, 18, 19, 20, 21),
    )


# Scenario Definitions
SCENARIOS = {
    "normal": {
        "label": "Normal Weather",
        "description": "Measured baseline weather and solar generation.",
        "irradiance_factor": 1.0,
        "cloud_offset": 0.0,
        "temp_delta_c": 0.0,
        "is_synthetic": False
    },
    "heavy_cloud": {
        "label": "Cloudy Weather",
        "description": "Synthetic scenario with solar irradiance reduced by 50% across the test period.",
        "irradiance_factor": 0.50,
        "cloud_offset": 0.50,
        "temp_delta_c": -2.0,
        "is_synthetic": True
    },
    "monsoon_prolonged": {
        "label": "Heavy Rain / Monsoon",
        "description": "Synthetic scenario with solar irradiance reduced by 75% and temperature lowered by 4°C.",
        "irradiance_factor": 0.25,
        "cloud_offset": 0.70,
        "temp_delta_c": -4.0,
        "is_synthetic": True
    },
    "sudden_drop": {
        "label": "Sudden Solar Drop",
        "description": "Synthetic 75% solar drop from 11:00 to 14:00 on the first test day.",
        "irradiance_factor": 0.25,
        "cloud_offset": 0.75,
        "temp_delta_c": -3.0,
        "is_synthetic": True
    },
    "multi_day_low": {
        "label": "Low Sunlight for Several Days",
        "description": "Synthetic 60% solar reduction during the first 72 hours of the test period.",
        "irradiance_factor": 0.40,
        "cloud_offset": 0.45,
        "temp_delta_c": -2.5,
        "is_synthetic": True
    },
    "recovery": {
        "label": "Weather Improving",
        "description": "Synthetic 80% solar drop through 11:00 on the first test day, followed by recovery.",
        "irradiance_factor": 0.20,
        "cloud_offset": 0.60,
        "temp_delta_c": -1.5,
        "is_synthetic": True
    }
}


def apply_weather_stress_scenario(
    df: pd.DataFrame,
    scenario_name: str,
    custom_factor: Optional[float] = None,
) -> pd.DataFrame:
    """
    Applies calibrated meteorological stress factors to a dataset slice.

    Preserves physical night zero-inflation: when solar elevation <= 0 or GHI <= 1.0,
    solar power is strictly 0.0 kW.
    """
    if scenario_name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: '{scenario_name}'. Valid options: {list(SCENARIOS.keys())}")

    config = SCENARIOS[scenario_name]
    factor = custom_factor if custom_factor is not None else config["irradiance_factor"]

    df_stressed = df.copy()
    if "time" in df_stressed.columns:
        df_stressed["time"] = pd.to_datetime(df_stressed["time"])

    # Extract hour array if available
    if "time" in df_stressed.columns:
        hours = df_stressed["time"].dt.hour.values
    else:
        hours = np.arange(len(df_stressed)) % 24

    if "time" in df_stressed.columns and len(df_stressed):
        elapsed_hours = (
            (df_stressed["time"] - df_stressed["time"].min()).dt.total_seconds().to_numpy() / 3600.0
        )
    else:
        elapsed_hours = np.arange(len(df_stressed), dtype=float)

    attenuation = np.ones(len(df_stressed), dtype=float)

    if scenario_name == "normal":
        attenuation[:] = 1.0

    elif scenario_name in ("heavy_cloud", "monsoon_prolonged"):
        attenuation[:] = factor

    elif scenario_name == "sudden_drop":
        # Model one localized midday event at the start of the test horizon.
        storm_mask = (elapsed_hours < 24.0) & (hours >= 11) & (hours <= 14)
        attenuation[storm_mask] = factor

    elif scenario_name == "multi_day_low":
        attenuation[elapsed_hours < 72.0] = factor

    elif scenario_name == "recovery":
        # Model one morning squall followed by clear conditions for the rest of the horizon.
        morning_mask = (elapsed_hours < 24.0) & (hours <= 11)
        attenuation[morning_mask] = factor

    # Apply attenuation to solar generation & irradiance features
    if "ac_power" in df_stressed.columns:
        df_stressed["ac_power_stressed"] = df_stressed["ac_power"] * attenuation
    else:
        df_stressed["ac_power_stressed"] = 0.0

    if "ghi" in df_stressed.columns:
        df_stressed["ghi_stressed"] = df_stressed["ghi"] * attenuation
    else:
        df_stressed["ghi_stressed"] = 0.0
    for window, column in ((3, "ghi_rolling_mean_3h"), (6, "ghi_rolling_mean_6h")):
        if column in df_stressed.columns:
            if "time" in df_stressed.columns:
                rolling_ghi = (
                    df_stressed.groupby("time")["ghi_stressed"]
                    .first()
                    .rolling(window=window, min_periods=1)
                    .mean()
                )
                df_stressed[column] = df_stressed["time"].map(rolling_ghi)
            else:
                df_stressed[column] = (
                    pd.Series(df_stressed["ghi_stressed"])
                    .rolling(window=window, min_periods=1)
                    .mean()
                    .to_numpy()
                )
    for column in ("direct_radiation", "dhi", "dni"):
        if column in df_stressed.columns:
            df_stressed[f"{column}_stressed"] = df_stressed[column] * attenuation

    if "cloud_cover_index" in df_stressed.columns:
        df_stressed["cloud_cover_index_stressed"] = np.clip(
            df_stressed["cloud_cover_index"] + config["cloud_offset"] * 100.0 * (attenuation < 1.0),
            0.0,
            100.0,
        )

    if "openmeteo_temperature" in df_stressed.columns:
        df_stressed["temp_stressed"] = (
            df_stressed["openmeteo_temperature"]
            + config["temp_delta_c"] * (attenuation < 1.0)
        )
    elif "sensor_temperature" in df_stressed.columns:
        df_stressed["temp_stressed"] = (
            df_stressed["sensor_temperature"]
            + config["temp_delta_c"] * (attenuation < 1.0)
        )
    else:
        df_stressed["temp_stressed"] = 25.0

    # Physical nighttime zero-inflation enforcement
    if "solar_elevation_deg" in df_stressed.columns:
        night_mask = (df_stressed["solar_elevation_deg"] <= 0.0) | (df_stressed["ghi_stressed"] <= 1.0)
        df_stressed.loc[night_mask, "ac_power_stressed"] = 0.0
        df_stressed.loc[night_mask, "ghi_stressed"] = 0.0
    else:
        night_mask = (hours < 6) | (hours > 18)
        df_stressed.loc[night_mask, "ac_power_stressed"] = 0.0
        df_stressed.loc[night_mask, "ghi_stressed"] = 0.0

    # Ensure non-negative bounds
    df_stressed["ac_power_stressed"] = np.maximum(0.0, df_stressed["ac_power_stressed"])
    df_stressed["ghi_stressed"] = np.maximum(0.0, df_stressed["ghi_stressed"])

    df_stressed["scenario_name"] = scenario_name
    df_stressed["scenario_label"] = config["label"]
    df_stressed["is_synthetic_scenario"] = config["is_synthetic"]
    df_stressed["attenuation_factor"] = attenuation

    return df_stressed


def evaluate_forecasting_under_stress(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    scenario_name: str,
    plant_id: int = 1,
) -> Dict[str, Any]:
    """
    Evaluates LightGBM and Ridge Regression forecasters against a stressed weather scenario.
    """
    # 1. Apply stress scenario to test horizon
    test_stressed = apply_weather_stress_scenario(test_df, scenario_name=scenario_name)

    # 2. Fit Ridge Baseline on training data
    ridge_features = [c for c in ["ghi", "openmeteo_temperature", "cos_zenith", "hour_sin", "hour_cos", "solar_elevation_deg"] if c in train_df.columns]
    ridge_pipeline = LinearBaselinePipeline(feature_cols=ridge_features, model_type="ridge", alpha=1.0)
    ridge_pipeline.fit(train_df)

    # 3. Fit LightGBM on training data
    lgb_model = LightGBMForecaster(n_estimators=100, max_depth=5, learning_rate=0.05)
    lgb_model.fit(train_df)

    # In stressed test set, features mirror stressed weather
    test_features = test_stressed.copy()
    if "ghi_stressed" in test_features.columns:
        test_features["ghi"] = test_features["ghi_stressed"]
    for column in ("direct_radiation", "dhi", "dni", "cloud_cover_index"):
        stressed_column = f"{column}_stressed"
        if stressed_column in test_features.columns:
            test_features[column] = test_features[stressed_column]
    if "temp_stressed" in test_features.columns and "openmeteo_temperature" in test_features.columns:
        test_features["openmeteo_temperature"] = test_features["temp_stressed"]

    # Generate predictions
    y_true = test_stressed["ac_power_stressed"].values
    y_pred_ridge = ridge_pipeline.predict(test_features, enforce_night_zero=True)
    y_pred_lgb = lgb_model.predict(test_features, enforce_night_zero=True)

    # Keep one measured-daylight mask across scenarios so RMSE values are comparable.
    is_day = test_df["ac_power"].to_numpy() > 10.0
    metrics_ridge = evaluate_forecast(y_true, y_pred_ridge, is_daylight=is_day, daylight_mape_min_actual=50.0)
    metrics_lgb = evaluate_forecast(y_true, y_pred_lgb, is_daylight=is_day, daylight_mape_min_actual=50.0)
    rated_capacity_mw = PLANT_RATED_CAPACITY_MW[plant_id]
    peak_actual_generation_kw = float(np.max(y_true))
    if peak_actual_generation_kw > rated_capacity_mw * 1000.0:
        raise ValueError(
            f"Plant {plant_id} scenario peak {peak_actual_generation_kw:.2f} kW exceeds "
            f"its rated capacity of {rated_capacity_mw:.1f} MW."
        )

    return {
        "plant_id": plant_id,
        "plant_rated_capacity_mw": rated_capacity_mw,
        "scenario_name": scenario_name,
        "scenario_label": SCENARIOS[scenario_name]["label"],
        "is_synthetic": SCENARIOS[scenario_name]["is_synthetic"],
        "mean_actual_generation_kw": round(float(np.mean(y_true)), 2),
        "total_solar_generation_7d_mwh": round(float(np.sum(y_true)) / 1000.0, 2),
        "peak_actual_generation_kw": round(peak_actual_generation_kw, 2),
        "forecast_test_start": pd.Timestamp(test_df["time"].min()).strftime("%Y-%m-%d %H:%M"),
        "forecast_test_end": pd.Timestamp(test_df["time"].max()).strftime("%Y-%m-%d %H:%M"),
        "forecast_test_hours": int(len(y_true)),
        "forecast_daylight_hours": int(np.sum(is_day)),
        "ridge_daylight_rmse_kw": round(float(metrics_ridge["daylight_rmse"]), 2),
        "ridge_daylight_mae_kw": round(float(metrics_ridge["daylight_mae"]), 2),
        "ridge_daylight_r2": round(float(metrics_ridge["daylight_r2"]), 4),
        "lgb_daylight_rmse_kw": round(float(metrics_lgb["daylight_rmse"]), 2),
        "lgb_daylight_mae_kw": round(float(metrics_lgb["daylight_mae"]), 2),
        "lgb_daylight_r2": round(float(metrics_lgb["daylight_r2"]), 4),
    }


def evaluate_battery_resilience_under_stress(
    df_day: pd.DataFrame,
    scenario_name: str,
    specs: Optional[BatterySpecs] = None,
    tariff: Optional[TOUTariff] = None,
    load_kw: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Evaluates PuLP LP BESS storage dispatch resilience during stressed weather conditions.
    """
    if specs is None:
        specs = BatterySpecs(
            capacity_kwh=10000.0,
            max_charge_kw=5000.0,
            max_discharge_kw=5000.0,
            soc_initial=0.20,
            soc_min=0.10,
            soc_max=0.90,
            degradation_cost_per_kwh=0.50,
        )
    if tariff is None:
        tariff = create_weather_stress_tariff()

    # Apply stress
    stressed_day = apply_weather_stress_scenario(df_day, scenario_name=scenario_name)
    solar_kw = stressed_day["ac_power_stressed"].values
    timestamps = pd.to_datetime(stressed_day["time"]) if "time" in stressed_day.columns else None

    # Solve PuLP optimization
    optimizer = BatteryOptimizerLP(specs=specs, tariff=tariff)
    opt_res = optimizer.optimize_dispatch(
        solar_kw=solar_kw,
        load_kw=load_kw,
        timestamps=timestamps,
        dt_hours=1.0,
        enforce_terminal_soc=True,
    )

    kpis = opt_res["kpi_summary"]
    sched_df = opt_res["schedule_df"]
    if opt_res["solver_status"] != "Optimal":
        raise RuntimeError(f"Battery resilience optimization failed: {opt_res['solver_status']}")

    # Calculate resilience indicators
    total_solar_kwh = float(np.sum(solar_kw))
    total_load_kwh = float(np.sum(sched_df["load_demand_kw"])) if "load_demand_kw" in sched_df else 0.0
    grid_import_bess_kwh = float(np.sum(sched_df["grid_import_with_bess_kw"]))
    grid_import_baseline_kwh = float(np.sum(sched_df["grid_import_unmanaged_kw"]))

    grid_dependency_pct = (grid_import_bess_kwh / total_load_kwh * 100.0) if total_load_kwh > 0 else 0.0
    storage_autonomy_pct = (100.0 - grid_dependency_pct)

    # Peak grid import surge compared to baseline clear sky
    peak_grid_import_kw = float(np.max(sched_df["grid_import_with_bess_kw"]))

    return {
        "scenario_name": scenario_name,
        "scenario_label": SCENARIOS[scenario_name]["label"],
        "is_synthetic": SCENARIOS[scenario_name]["is_synthetic"],
        "total_solar_generation_mwh": round(total_solar_kwh / 1000.0, 2),
        "total_load_demand_mwh": round(total_load_kwh / 1000.0, 2),
        "grid_import_with_bess_mwh": round(grid_import_bess_kwh / 1000.0, 2),
        "grid_import_without_bess_mwh": round(grid_import_baseline_kwh / 1000.0, 2),
        "grid_dependency_pct": round(grid_dependency_pct, 1),
        "storage_autonomy_pct": round(storage_autonomy_pct, 1),
        "grid_dependency_definition": "grid imports / modeled facility demand",
        "storage_autonomy_definition": "100% - grid dependency",
        "battery_degradation_cost_per_kwh": specs.degradation_cost_per_kwh,
        "battery_charge_efficiency_pct": specs.charge_efficiency * 100.0,
        "battery_discharge_efficiency_pct": specs.discharge_efficiency * 100.0,
        "tariff_off_peak_inr_per_kwh": tariff.off_peak_rate,
        "tariff_normal_inr_per_kwh": tariff.normal_rate,
        "tariff_peak_inr_per_kwh": tariff.peak_rate,
        "tariff_export_inr_per_kwh": tariff.export_feedin_rate,
        "tariff_source": "Week2_TOU_Tariff_Cost_Matrix_Plant1_Plant2_2020.csv",
        "peak_grid_import_mw": round(peak_grid_import_kw / 1000.0, 2),
        "cost_without_bess": round(float(kpis["cost_without_bess"]), 2),
        "cost_with_bess": round(float(kpis["cost_with_bess"]), 2),
        "net_arbitrage_savings": round(float(kpis["net_arbitrage_savings"]), 2),
        "solar_self_consumption_pct": round(float(kpis["solar_self_consumption_with_bess_pct"]), 1),
        "battery_throughput_mwh": round(float(kpis["battery_total_throughput_kwh"]) / 1000.0, 2),
        "min_soc_pct": round(float(sched_df["battery_soc_pct"].min()), 1),
        "max_soc_pct": round(float(sched_df["battery_soc_pct"].max()), 1),
        "schedule_df": sched_df,
    }


def run_full_weather_stress_suite(plant_id: int = 1, save_artifacts: bool = True) -> Dict[str, Any]:
    """
    Executes the full Week 4 Extreme Weather Stress Test suite across all scenarios:
    1. Generates forecast stress metrics
    2. Runs BESS battery resilience LP dispatch
    3. Exports reports/week4_weather_stress_summary.csv and publication figures
    """
    df_hourly = load_processed_handoff(plant_id=plant_id, freq="hourly")
    train_df, test_df = temporal_train_test_split(df_hourly, test_days=7)
    test_24h = test_df.tail(24).copy().reset_index(drop=True)
    normal_solar_kw = apply_weather_stress_scenario(
        test_24h, scenario_name="normal"
    )["ac_power_stressed"].to_numpy()
    common_load_kw = create_synthetic_load_profile(normal_solar_kw, test_24h["time"])

    forecast_results = []
    resilience_results = []

    for sc_name in SCENARIOS.keys():
        # 1. Forecasting stress
        f_res = evaluate_forecasting_under_stress(train_df, test_df, sc_name, plant_id=plant_id)
        forecast_results.append(f_res)

        # 2. Battery resilience stress
        b_res = evaluate_battery_resilience_under_stress(test_24h, sc_name, load_kw=common_load_kw)
        # Store clean dictionary without DataFrame for tabular serialization
        b_dict = {k: v for k, v in b_res.items() if k != "schedule_df"}
        b_dict["plant_id"] = plant_id
        resilience_results.append(b_dict)

    df_forecast = pd.DataFrame(forecast_results)
    df_resilience = pd.DataFrame(resilience_results)

    # Combined summary table
    df_summary = pd.merge(
        df_forecast,
        df_resilience,
        on=["plant_id", "scenario_name", "scenario_label", "is_synthetic"],
    )

    if save_artifacts:
        reports_dir = ROOT_DIR / "reports"
        figures_dir = reports_dir / "figures"
        reports_dir.mkdir(parents=True, exist_ok=True)
        figures_dir.mkdir(parents=True, exist_ok=True)

        df_summary.to_csv(reports_dir / "week4_weather_stress_summary.csv", index=False)
        df_forecast.to_csv(reports_dir / "week4_forecast_stress_metrics.csv", index=False)
        df_resilience.to_csv(reports_dir / "week4_battery_resilience.csv", index=False)

        # 1. Plot Weather Stress Forecasting Comparison
        fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
        x = np.arange(len(df_forecast))
        width = 0.35
        ax.bar(x - width/2, df_forecast["ridge_daylight_rmse_kw"] / 1000.0, width, label="Ridge Baseline", color="#3b82f6")
        ax.bar(x + width/2, df_forecast["lgb_daylight_rmse_kw"] / 1000.0, width, label="LightGBM (GBDT)", color="#10b981")
        ax.set_ylabel("Daylight RMSE (MW)", fontsize=11, fontweight="bold")
        ax.set_title(f"Plant {plant_id}: Solar Forecasting Accuracy Under Extreme Weather Stress", fontsize=12, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace("_", " ").title() for s in df_forecast["scenario_name"]], rotation=25, ha="right", fontsize=9)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        ax.legend()
        plt.tight_layout()
        plt.savefig(figures_dir / "week4_weather_stress_comparison.png")
        plt.close(fig)

        # 2. Plot Battery Resilience & Grid Dependence
        fig2, ax2 = plt.subplots(figsize=(10, 5), dpi=300)
        ax2.plot(df_resilience["scenario_label"], df_resilience["grid_dependency_pct"], marker="o", color="#ef4444", linewidth=2.5, label="Grid Dependency (%)")
        ax2.plot(df_resilience["scenario_label"], df_resilience["storage_autonomy_pct"], marker="s", color="#10b981", linewidth=2.5, label="Storage Autonomy (%)")
        ax2.set_ylabel("Percentage (%)", fontsize=11, fontweight="bold")
        ax2.set_title(f"Plant {plant_id}: BESS Energy Autonomy & Grid Stress Under Weather Scenarios", fontsize=12, fontweight="bold")
        ax2.set_xticks(range(len(df_resilience)))
        ax2.set_xticklabels(df_resilience["scenario_label"], rotation=25, ha="right", fontsize=8.5)
        ax2.grid(linestyle="--", alpha=0.5)
        ax2.legend()
        plt.tight_layout()
        plt.savefig(figures_dir / "week4_battery_resilience.png")
        plt.close(fig2)

    return {
        "plant_id": plant_id,
        "summary_df": df_summary,
        "forecast_df": df_forecast,
        "resilience_df": df_resilience,
    }


if __name__ == "__main__":
    print("Executing Week 4 Weather Stress-Testing Suite...")
    res = run_full_weather_stress_suite(plant_id=1, save_artifacts=True)
    print("[OK] Weather stress-testing suite executed successfully.")
    print("Summary:")
    print(res["summary_df"][["scenario_name", "ridge_daylight_rmse_kw", "lgb_daylight_rmse_kw", "grid_dependency_pct", "net_arbitrage_savings"]])

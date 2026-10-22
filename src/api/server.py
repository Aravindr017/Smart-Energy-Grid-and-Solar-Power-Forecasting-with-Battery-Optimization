"""
FastAPI Server for Solar Power Forecasting & Battery Energy Storage Optimization
Provides REST APIs for the React + Tailwind CSS dashboard.
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io

# Ensure project root is available in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.data.loader import load_processed_handoff
from src.optimization.battery_lp import BatterySpecs, TOUTariff, BatteryOptimizerLP

app = FastAPI(
    title="Solar Grid Intelligence & BESS Optimization API",
    description="REST backend for 24-Hour Solar Forecasting and Battery Energy Arbitrage",
    version="1.0.0"
)

# Enable CORS for local React Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for processed datasets
_DATA_CACHE: Dict[str, pd.DataFrame] = {}


def get_cached_dataset(plant_id: int, freq: str) -> pd.DataFrame:
    cache_key = f"{plant_id}_{freq}"
    if cache_key not in _DATA_CACHE:
        df = load_processed_handoff(plant_id=plant_id, freq=freq)
        _DATA_CACHE[cache_key] = df
    return _DATA_CACHE[cache_key]


# -------------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------------
class OptimizationRequest(BaseModel):
    plant_id: int = Field(1, ge=1, le=2, description="Plant ID (1 or 2)")
    battery_capacity_mwh: float = Field(10.0, ge=0.5, le=50.0, description="Battery capacity in MWh")
    max_inverter_power_mw: float = Field(5.0, ge=0.2, le=25.0, description="Inverter rating in MW")
    round_trip_efficiency_pct: float = Field(90.25, ge=60.0, le=99.0, description="Round-trip efficiency %")
    initial_soc_pct: float = Field(20.0, ge=10.0, le=80.0, description="Initial State-of-Charge %")
    off_peak_rate: float = Field(0.05, ge=0.01, le=1.0, description="Off-peak tariff ($/kWh)")
    normal_rate: float = Field(0.10, ge=0.01, le=1.0, description="Normal shoulder tariff ($/kWh)")
    peak_rate: float = Field(0.25, ge=0.01, le=2.0, description="Evening peak tariff ($/kWh)")
    export_feedin_rate: float = Field(0.04, ge=0.0, le=0.5, description="Export feed-in tariff ($/kWh)")
    degradation_cost_per_kwh: float = Field(0.005, ge=0.0, le=0.05, description="Battery degradation wear ($/kWh)")
    installed_cost_per_kwh: float = Field(250.0, ge=50.0, le=800.0, description="Estimated battery CAPEX ($/kWh)")


# -------------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------------
@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "system": "Solar Grid & Battery LP Optimization Engine",
        "version": "1.0.0",
        "milestone": "Week 3 MVP",
        "plants_available": [1, 2]
    }


@app.get("/api/plants")
def get_plants():
    return [
        {
            "id": 1,
            "name": "Plant 1 (Gandikota Solar Farm)",
            "plant_code": 3418353,
            "latitude": 14.80,
            "longitude": 78.18,
            "elevation_m": 203,
            "inverters_count": 22,
            "rated_capacity_mw": 29.5,
            "location_name": "Andhra Pradesh, India",
            "data_span_days": 34
        },
        {
            "id": 2,
            "name": "Plant 2 (Ananthapuramu Solar Park)",
            "plant_code": 4135001,
            "latitude": 14.38,
            "longitude": 77.50,
            "elevation_m": 491,
            "inverters_count": 22,
            "rated_capacity_mw": 26.2,
            "location_name": "Andhra Pradesh, India",
            "data_span_days": 34
        }
    ]


@app.get("/api/overview")
def get_overview(
    plant_id: int = Query(1, ge=1, le=2),
    granularity: str = Query("hourly", pattern="^(15min|15min_plant|hourly)$"),
    limit: int = Query(96, ge=24, le=1000)
):
    try:
        df_raw = get_cached_dataset(plant_id, granularity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dataset: {str(e)}")

    if "source_key" in df_raw.columns:
        # Aggregate by time
        numeric_cols = [c for c in ["sensor_irradiation", "sensor_temperature", "module_temperature", "openmeteo_temperature", "humidity", "ghi", "direct_radiation"] if c in df_raw.columns]
        agg_rules = {"ac_power": "sum", "dc_power": "sum"}
        for c in numeric_cols:
            agg_rules[c] = "mean"
        df = df_raw.groupby("time").agg(agg_rules).reset_index()
    else:
        df = df_raw.copy()

    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time")

    dt_hours = 0.25 if "15min" in granularity else 1.0
    total_energy_mwh = float((df["ac_power"].sum() * dt_hours) / 1000.0)
    peak_ac_kw = float(df["ac_power"].max())
    avg_ac_kw = float(df["ac_power"].mean())
    total_records = len(df)

    # Return the latest slice for visual presentation
    recent_slice = df.tail(limit).copy()
    timeseries = []
    for _, row in recent_slice.iterrows():
        timeseries.append({
            "time": row["time"].strftime("%Y-%m-%d %H:%M"),
            "ac_power_kw": round(float(row.get("ac_power", 0.0)), 1),
            "dc_power_kw": round(float(row.get("dc_power", 0.0)), 1),
            "ghi": round(float(row.get("ghi", 0.0)), 1) if "ghi" in row else 0.0,
            "ambient_temp_c": round(float(row.get("openmeteo_temperature", row.get("sensor_temperature", 0.0))), 1),
            "module_temp_c": round(float(row.get("module_temperature", 0.0)), 1)
        })

    return {
        "plant_id": plant_id,
        "granularity": granularity,
        "kpis": {
            "total_energy_mwh": round(total_energy_mwh, 1),
            "peak_ac_kw": round(peak_ac_kw, 1),
            "avg_ac_kw": round(avg_ac_kw, 1),
            "total_records": total_records,
            "date_start": df["time"].min().strftime("%Y-%m-%d"),
            "date_end": df["time"].max().strftime("%Y-%m-%d"),
        },
        "timeseries": timeseries
    }


@app.get("/api/forecast")
def get_forecast(
    plant_id: int = Query(1, ge=1, le=2),
    slice_length: int = Query(96, ge=24, le=672)
):
    """
    Returns Week 2 24-Hour forecasting benchmarks, prediction trajectories,
    feature importance, and computed forecast uncertainty bounds.
    """
    # 1. Summary Metrics
    metrics_file = ROOT_DIR / "reports" / "week2_forecasting_metrics_summary.csv"
    metrics_list = []
    if metrics_file.exists():
        df_m = pd.read_csv(metrics_file)
        plant_m = df_m[df_m["plant_id"] == plant_id].copy()
        for _, row in plant_m.iterrows():
            metrics_list.append({
                "model": row["model"],
                "daylight_rmse_kw": round(float(row["daylight_rmse"]), 2),
                "daylight_mape_pct": round(float(row["daylight_mape_pct"]), 2),
                "daylight_mae_kw": round(float(row["daylight_mae"]), 2),
                "daylight_r2": round(float(row["daylight_r2"]), 4),
                "overall_rmse_kw": round(float(row["rmse_overall"]), 2),
                "daylight_nrmse_pct": round(float(row["daylight_nrmse_pct"]), 2)
            })

    # 2. Predictions & Forecast Bounds
    pred_file = ROOT_DIR / "reports" / f"plant{plant_id}_week2_forecasting_predictions.csv"
    if not pred_file.exists():
        raise HTTPException(status_code=404, detail="Forecast predictions CSV not found.")

    df_p = pd.read_csv(pred_file)
    df_p["time"] = pd.to_datetime(df_p["time"])

    # Aggregate across inverters to plant level
    num_cols = [c for c in df_p.columns if c not in ["time", "source_key"]]
    df_agg = df_p.groupby("time")[num_cols].sum().reset_index().sort_values("time")

    # Compute empirical error standard deviation for forecast uncertainty bounds (90% prediction interval)
    residuals = df_agg["actual_ac_power"] - df_agg["pred_lightgbm"]
    # Mask daytime only for residual std
    daytime_mask = df_agg["actual_ac_power"] > 50.0
    daytime_std = float(residuals[daytime_mask].std()) if daytime_mask.sum() > 0 else 500.0

    # Upper and lower bounds (1.645 * std for 90% confidence), clamped at 0
    df_agg["lower_bound"] = np.maximum(0.0, df_agg["pred_lightgbm"] - 1.645 * daytime_std)
    df_agg["upper_bound"] = np.maximum(0.0, df_agg["pred_lightgbm"] + 1.645 * daytime_std)
    # Nighttime zero clamping
    night_mask = df_agg["pred_lightgbm"] < 10.0
    df_agg.loc[night_mask, "lower_bound"] = 0.0
    df_agg.loc[night_mask, "upper_bound"] = 0.0

    # Take the latest slice for visual clarity
    df_slice = df_agg.tail(slice_length)

    predictions = []
    for _, row in df_slice.iterrows():
        predictions.append({
            "time": row["time"].strftime("%m/%d %H:%M"),
            "actual": round(float(row.get("actual_ac_power", 0.0)), 1),
            "lightgbm": round(float(row.get("pred_lightgbm", 0.0)), 1),
            "prophet": round(float(row.get("pred_prophet", 0.0)), 1),
            "ridge": round(float(row.get("pred_ridge", 0.0)), 1),
            "persistence": round(float(row.get("pred_persistence", 0.0)), 1),
            "lower_bound": round(float(row.get("lower_bound", 0.0)), 1),
            "upper_bound": round(float(row.get("upper_bound", 0.0)), 1)
        })

    # 3. Feature Importance
    feat_file = ROOT_DIR / "reports" / f"plant{plant_id}_lightgbm_feature_importance.csv"
    features = []
    if feat_file.exists():
        df_f = pd.read_csv(feat_file)
        for _, row in df_f.head(10).iterrows():
            features.append({
                "feature": str(row["feature"]).replace("_", " ").title(),
                "importance": int(row["importance"])
            })

    return {
        "plant_id": plant_id,
        "metrics": metrics_list,
        "predictions": predictions,
        "feature_importance": features,
        "bounds_info": {
            "confidence_level": "90%",
            "std_error_kw": round(daytime_std, 1),
            "methodology": "Residual standard error envelope with physical zero truncation"
        }
    }


@app.post("/api/optimize")
def run_optimization(req: OptimizationRequest):
    """
    Executes PuLP 24-Hour Linear Programming battery arbitrage and returns
    dispatch schedules, Duck Curve mitigation, State-of-Charge progression,
    and financial savings breakdown.
    """
    # Load 24-hour test day from hourly plant dataset
    try:
        df_hourly = get_cached_dataset(req.plant_id, "hourly")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load hourly data: {str(e)}")

    day_slice = df_hourly.tail(24).copy().reset_index(drop=True)
    timestamps = pd.to_datetime(day_slice["time"])

    # Configure Battery Specs
    one_way_eff = float(np.sqrt(req.round_trip_efficiency_pct / 100.0))
    batt_cap_kwh = req.battery_capacity_mwh * 1000.0
    max_p_kw = req.max_inverter_power_mw * 1000.0

    specs = BatterySpecs(
        capacity_kwh=batt_cap_kwh,
        max_charge_kw=max_p_kw,
        max_discharge_kw=max_p_kw,
        charge_efficiency=one_way_eff,
        discharge_efficiency=one_way_eff,
        soc_min=0.10,
        soc_max=0.90,
        soc_initial=req.initial_soc_pct / 100.0,
        degradation_cost_per_kwh=req.degradation_cost_per_kwh,
    )

    tariff = TOUTariff(
        off_peak_rate=req.off_peak_rate,
        normal_rate=req.normal_rate,
        peak_rate=req.peak_rate,
        export_feedin_rate=req.export_feedin_rate,
    )

    optimizer = BatteryOptimizerLP(specs=specs, tariff=tariff)
    opt_res = optimizer.optimize_dispatch(
        solar_kw=day_slice["ac_power"].values,
        timestamps=timestamps,
        dt_hours=1.0,
        enforce_terminal_soc=True,
    )

    kpis = opt_res["kpi_summary"]
    sched_df = opt_res["schedule_df"]

    # Financial analysis
    daily_savings = float(kpis["net_arbitrage_savings"])
    annual_savings = round(daily_savings * 365.0, 2)
    total_capex = round(batt_cap_kwh * req.installed_cost_per_kwh, 2)
    simple_payback_years = round(total_capex / annual_savings, 2) if annual_savings > 0 else 999.0

    # Hourly schedule records
    schedule_rows = []
    for idx, row in sched_df.iterrows():
        hour_int = int(row["step"])
        tier = "Peak" if hour_int in tariff.peak_hours else ("Off-Peak" if hour_int in tariff.off_peak_hours else "Normal")
        schedule_rows.append({
            "hour": f"{hour_int:02d}:00",
            "step": hour_int,
            "tariff_rate": round(float(row["import_tariff"]), 3),
            "tariff_tier": tier,
            "solar_mw": round(float(row["solar_generation_kw"]) / 1000.0, 2),
            "demand_mw": round(float(row["load_demand_kw"]) / 1000.0, 2),
            "unmanaged_import_mw": round(float(row["grid_import_unmanaged_kw"]) / 1000.0, 2),
            "managed_import_mw": round(float(row["grid_import_with_bess_kw"]) / 1000.0, 2),
            "charge_mw": round(float(row["battery_charge_kw"]) / 1000.0, 2),
            "discharge_mw": round(float(row["battery_discharge_kw"]) / 1000.0, 2),
            "battery_energy_mwh": round(float(row["battery_energy_kwh"]) / 1000.0, 2),
            "battery_soc_pct": round(float(row["battery_soc_pct"]), 1),
        })

    # SoC Gauge metrics
    min_soc = float(sched_df["battery_soc_pct"].min())
    max_soc = float(sched_df["battery_soc_pct"].max())
    final_soc = float(sched_df["battery_soc_pct"].iloc[-1])

    return {
        "kpis": kpis,
        "schedule": schedule_rows,
        "financials": {
            "daily_savings": daily_savings,
            "annual_savings_projected": annual_savings,
            "estimated_capex": total_capex,
            "simple_payback_years": simple_payback_years,
            "solar_self_consumption_gain_pct": round(kpis["solar_self_consumption_with_bess_pct"] - kpis["solar_self_consumption_without_bess_pct"], 2),
            "peak_demand_shaved_mw": round(kpis["peak_demand_shaved_kw"] / 1000.0, 2)
        },
        "soc_gauge": {
            "initial_soc_pct": req.initial_soc_pct,
            "final_soc_pct": final_soc,
            "min_soc_pct": min_soc,
            "max_soc_pct": max_soc,
            "safe_min_bound_pct": 10.0,
            "safe_max_bound_pct": 90.0,
            "terminal_condition_met": bool(final_soc >= (req.initial_soc_pct - 0.5))
        }
    }


@app.get("/api/dataset")
def get_dataset_sample(
    plant_id: int = Query(1, ge=1, le=2),
    limit: int = Query(50, ge=10, le=200)
):
    df = get_cached_dataset(plant_id, "hourly")
    cols = [c for c in ["time", "ac_power", "dc_power", "sensor_irradiation", "sensor_temperature", "module_temperature", "openmeteo_temperature", "humidity", "ghi"] if c in df.columns]
    records = df[cols].tail(limit).to_dict(orient="records")
    return {
        "plant_id": plant_id,
        "total_rows": len(df),
        "columns": cols,
        "records": records
    }


# Mount production React build if dist exists
dist_dir = ROOT_DIR / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")


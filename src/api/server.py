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
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
import io

# Ensure project root is available in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.data.loader import load_processed_handoff
from src.data.weather_live import fetch_live_openmeteo_forecast
from src.models.forecasting import generate_24h_ahead_solar_forecast
from src.optimization.battery_lp import BatterySpecs, TOUTariff, BatteryOptimizerLP
from src.optimization.tariff_config import (
    BATTERY_DEGRADATION_COST_INR_PER_KWH,
    BATTERY_INSTALLED_COST_INR_PER_KWH,
    CURRENCY_CODE,
    CURRENCY_SYMBOL,
    EXPORT_FEEDIN_RATE_INR_PER_KWH,
    NORMAL_RATE_INR_PER_KWH,
    OFF_PEAK_RATE_INR_PER_KWH,
    PEAK_RATE_INR_PER_KWH,
    get_tariff_config,
)
from src.analysis.weather_stress_test import (
    PLANT_RATED_CAPACITY_MW,
    SCENARIOS,
    run_full_weather_stress_suite,
)
from src.analysis.carbon_accounting import (
    GRID_EMISSION_PROVENANCE,
    run_carbon_scenario_analysis,
    calculate_carbon_offsets,
)

_WEATHER_STRESS_CACHE: Dict[int, Dict[str, Any]] = {}


def generate_executive_pdf(*args, **kwargs):
    from src.visualization.executive_report import generate_executive_pdf as _generate
    return _generate(*args, **kwargs)

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
    off_peak_rate: float = Field(OFF_PEAK_RATE_INR_PER_KWH, ge=0.0, le=100.0, description="Simulated off-peak tariff (INR/kWh)")
    normal_rate: float = Field(NORMAL_RATE_INR_PER_KWH, ge=0.0, le=100.0, description="Simulated normal tariff (INR/kWh)")
    peak_rate: float = Field(PEAK_RATE_INR_PER_KWH, ge=0.0, le=100.0, description="Simulated peak tariff (INR/kWh)")
    export_feedin_rate: float = Field(EXPORT_FEEDIN_RATE_INR_PER_KWH, ge=0.0, le=50.0, description="Assumed solar export feed-in tariff (INR/kWh)")
    degradation_cost_per_kwh: float = Field(BATTERY_DEGRADATION_COST_INR_PER_KWH, ge=0.0, le=100.0, description="Estimated battery degradation wear (INR/kWh)")
    installed_cost_per_kwh: float = Field(BATTERY_INSTALLED_COST_INR_PER_KWH, ge=100.0, le=100000.0, description="Estimated battery installation cost (INR/kWh)")
    use_forecast: bool = Field(True, description="Whether to optimize on upcoming 24-hour live weather forecast (True) or historical baseline slice (False)")



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


@app.get("/api/tariff-config")
def get_tariff_configuration():
    """Return the shared simulated INR tariffs and associated cost assumptions."""
    return get_tariff_config()


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


@app.get("/api/weather/live")
def get_live_weather(
    plant_id: int = Query(1, ge=1, le=2, description="Plant ID (1 or 2)")
):
    """
    Returns live Open-Meteo weather forecast and current meteorological conditions
    for the plant's geographic coordinates, with caching and historical fallback.
    """
    try:
        return fetch_live_openmeteo_forecast(plant_id=plant_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch live weather: {str(exc)}")


@app.get("/api/forecast/live-24h")
def get_live_24h_forecast(
    plant_id: int = Query(1, ge=1, le=2, description="Plant ID (1 or 2)")
):
    """
    Generates genuine operational 24-hour ahead solar power forecast using live
    Open-Meteo weather forecast variables, solar geometry, and pre-trained GBDT/Prophet models.
    """
    try:
        return generate_24h_ahead_solar_forecast(plant_id=plant_id, horizon_hours=24)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate 24h solar forecast: {str(exc)}")


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

    # Upper and lower bounds (1.645 * std for approximate 90% empirical coverage), clamped at 0
    df_agg["lower_bound"] = np.maximum(0.0, df_agg["pred_lightgbm"] - 1.645 * daytime_std)
    df_agg["upper_bound"] = np.maximum(df_agg["lower_bound"], df_agg["pred_lightgbm"] + 1.645 * daytime_std)
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
            "xgboost": round(float(row.get("pred_xgboost", row.get("pred_lightgbm", 0.0))), 1),
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

    # 4. Live 24-Hour Operational Forecast (Next 24h from Open-Meteo)
    live_24h = None
    try:
        live_24h = generate_24h_ahead_solar_forecast(plant_id=plant_id, horizon_hours=24)
    except Exception:
        pass

    return {
        "plant_id": plant_id,
        "metrics": metrics_list,
        "predictions": predictions,
        "feature_importance": features,
        "live_24h_forecast": live_24h,
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
    Can optimize on upcoming 24-hour solar forecast (req.use_forecast=True) or historical slice.
    """
    solar_kw_array = None
    timestamps = None
    data_source_description = "Upcoming 24-Hour Solar Forecast (Live Open-Meteo)"
    is_future = True

    if req.use_forecast:
        try:
            fc = generate_24h_ahead_solar_forecast(plant_id=req.plant_id, horizon_hours=24)
            timeline = fc.get("timeline", [])
            if len(timeline) == 24:
                solar_kw_array = np.array([float(step["selected_solar_kw"]) for step in timeline], dtype=float)
                timestamps = pd.to_datetime([step["timestamp"] for step in timeline])
                is_future = True
                data_source_description = f"Upcoming 24-Hour Solar Forecast ({fc.get('data_source', 'Live Open-Meteo')})"
        except Exception:
            solar_kw_array = None

    if solar_kw_array is None:
        try:
            df_hourly = get_cached_dataset(req.plant_id, "hourly")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load hourly data: {str(e)}")

        day_slice = df_hourly.tail(24).copy().reset_index(drop=True)
        solar_kw_array = day_slice["ac_power"].values
        timestamps = pd.to_datetime(day_slice["time"])
        is_future = False
        data_source_description = "Historical Hourly Generation (24-Hour Baseline Slice)"

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
        solar_kw=solar_kw_array,
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
        # "step" is only the row's position in the 24-hour optimization horizon.
        # Tariff periods must be classified using the actual clock hour from
        # the corresponding timestamp, otherwise a forecast starting at (for
        # example) 08:00 will incorrectly label step 0 as 00:00.
        step = int(row["step"])
        t_obj = timestamps[idx] if timestamps is not None and idx < len(timestamps) else None

        if t_obj is not None:
            t_obj = pd.Timestamp(t_obj)
            clock_hour = t_obj.hour
            t_label = t_obj.strftime("%H:%M")
            t_iso = t_obj.strftime("%Y-%m-%d %H:%M")
        else:
            # Fallback for schedules without supplied timestamps. The optimizer
            # uses a repeating 24-hour tariff in this case.
            clock_hour = step % 24
            t_label = f"{clock_hour:02d}:00"
            t_iso = ""

        tier = (
            "Peak" if clock_hour in tariff.peak_hours
            else "Off-Peak" if clock_hour in tariff.off_peak_hours
            else "Normal"
        )
        schedule_rows.append({
            "hour": t_label,
            "step": step,
            "timestamp": t_iso,
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
        "currency_code": CURRENCY_CODE,
        "currency_symbol": CURRENCY_SYMBOL,
        "tariff_assumptions": {
            "off_peak_rate_inr_per_kwh": tariff.off_peak_rate,
            "normal_rate_inr_per_kwh": tariff.normal_rate,
            "peak_rate_inr_per_kwh": tariff.peak_rate,
            "export_feedin_rate_inr_per_kwh": tariff.export_feedin_rate,
            "disclaimer": "Financial results are estimates based on simulated tariff assumptions, not actual utility bills or guaranteed savings.",
        },
        "data_source": data_source_description,
        "is_future_forecast": is_future,
        "demand_assumption": "Facility baseline load demand is a calibrated synthetic scenario scaled to plant capacity; actual utility meter telemetry is unavailable.",
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


@app.get("/api/duck-curve")
def get_duck_curve(
    date: Optional[str] = Query(None, description="Date filter YYYY-MM-DD"),
    limit: int = Query(96, ge=24, le=672, description="Slice length in 15-minute intervals")
):
    """
    Returns Duck Curve telemetry: simulated grid demand, solar generation,
    and net load (demand - solar) at 15-minute resolution.
    Explicitly identifies demand as synthetic simulation.
    """
    duck_file = ROOT_DIR / "data" / "processed" / "duck_curve_demo_15min.csv"
    if not duck_file.exists():
        raise HTTPException(status_code=404, detail="Duck Curve processed dataset not found.")

    df_duck = pd.read_csv(duck_file)
    df_duck["dt"] = pd.to_datetime(df_duck["timestamp"])
    df_duck["date"] = df_duck["dt"].dt.strftime("%Y-%m-%d")

    available_dates = sorted(df_duck["date"].unique().tolist())
    if date and date in available_dates:
        df_slice = df_duck[df_duck["date"] == date].copy().sort_values("dt")
    else:
        # Default to the first full 24h day or tail(limit)
        df_slice = df_duck.head(limit).copy().sort_values("dt")

    solar_mw = df_slice["total_solar_generation_kw"].values
    demand_mw = df_slice["system_demand_synthetic_kw"].values
    net_load_mw = df_slice["illustrative_net_load_kw"].values

    peak_demand = float(np.max(demand_mw)) if len(demand_mw) > 0 else 0.0
    min_net = float(np.min(net_load_mw)) if len(net_load_mw) > 0 else 0.0
    max_solar = float(np.max(solar_mw)) if len(solar_mw) > 0 else 0.0
    belly_drop = peak_demand - min_net

    # Estimate evening ramp rate (max positive slope over 1 hour = 4 steps in evening 16:00-21:00)
    hours = df_slice["dt"].dt.hour.values
    evening_mask = (hours >= 16) & (hours <= 21)
    if np.sum(evening_mask) >= 4:
        ev_net = net_load_mw[evening_mask]
        ramp_rates = [ev_net[i + 4] - ev_net[i] for i in range(len(ev_net) - 4)]
        evening_ramp_mw_hr = float(max(ramp_rates)) if ramp_rates else 0.0
    else:
        evening_ramp_mw_hr = 0.0

    timeseries = []
    for _, row in df_slice.iterrows():
        timeseries.append({
            "timestamp": row["timestamp"],
            "time_label": row["dt"].strftime("%H:%M"),
            "date": row["date"],
            "solar_generation_mw": round(float(row["total_solar_generation_kw"]), 2),
            "grid_demand_mw": round(float(row["system_demand_synthetic_kw"]), 2),
            "net_load_mw": round(float(row["illustrative_net_load_kw"]), 2),
            "is_interpolated": bool(row.get("generation_interpolated", False))
        })

    return {
        "data_source_label": "Simulated Grid Demand Scenario",
        "is_synthetic_demand": True,
        "disclaimer": "Grid demand values are calibrated synthetic simulation scenarios scaled to plant capacity; actual regional utility telemetry is unavailable.",
        "selected_date": date or (df_slice["date"].iloc[0] if len(df_slice) > 0 else ""),
        "available_dates": available_dates,
        "total_records": len(timeseries),
        "metrics": {
            "peak_grid_demand_mw": round(peak_demand, 2),
            "min_midday_net_load_mw": round(min_net, 2),
            "max_midday_solar_mw": round(max_solar, 2),
            "belly_depth_drop_mw": round(belly_drop, 2),
            "evening_ramp_rate_mw_per_hour": round(evening_ramp_mw_hr, 2)
        },
        "timeseries": timeseries
    }


# -------------------------------------------------------------------------
# Week 4 Deliverables: Weather Stress, Carbon Accounting & Executive Report
# -------------------------------------------------------------------------
@app.get("/api/weather-stress")
def get_weather_stress(
    plant_id: int = Query(1, ge=1, le=2, description="Plant ID (1 or 2)"),
    scenario: Optional[str] = Query(None, description="Filter specific scenario")
):
    """
    Returns extreme-weather stress testing results:
    - Scenarios metadata & physical definitions
    - Multi-scenario summary metrics (generation, forecast errors, battery resilience)
    - Ridge vs LightGBM performance comparison under meteorological anomalies
    """
    if hasattr(plant_id, "default"):
        plant_id = plant_id.default
    if hasattr(scenario, "default"):
        scenario = scenario.default

    if plant_id not in _WEATHER_STRESS_CACHE:
        _WEATHER_STRESS_CACHE[plant_id] = run_full_weather_stress_suite(
            plant_id=plant_id,
            save_artifacts=False,
        )

    result = _WEATHER_STRESS_CACHE[plant_id]
    df_summary = result["summary_df"]
    df_fc = result["forecast_df"]
    df_batt = result["resilience_df"]

    if scenario:
        df_summary = df_summary[df_summary["scenario_name"] == scenario]
        df_fc = df_fc[df_fc["scenario_name"] == scenario]
        df_batt = df_batt[df_batt["scenario_name"] == scenario]

    scenarios_meta = [
        {"name": k, "label": v["label"], "description": v["description"], "is_synthetic": v["is_synthetic"]}
        for k, v in SCENARIOS.items()
    ]

    return {
        "plant_id": plant_id,
        "rated_capacity_mw": PLANT_RATED_CAPACITY_MW[plant_id],
        "scenarios_metadata": scenarios_meta,
        "selected_scenario": scenario,
        "summary": df_summary.to_dict(orient="records"),
        "forecast_stress_metrics": df_fc.to_dict(orient="records"),
        "battery_resilience": df_batt.to_dict(orient="records"),
    }


@app.get("/api/carbon")
def get_carbon_accounting(
    plant_id: int = Query(1, ge=1, le=2, description="Plant ID (1 or 2)"),
    emission_factor: Optional[float] = Query(None, ge=0.1, le=2.0, description="Custom grid emission factor (kg CO2e/kWh)")
):
    """
    Returns carbon-offset accounting telemetry and sensitivity analysis:
    - Official Central Electricity Authority (CEA v19) baseline emission factor (0.716 kg CO2e/kWh)
    - Grid intensity sensitivity comparison across 4 carbon regimes
    - Weather stress scenario avoided emissions
    - Custom user-specified emission factor recalculation
    """
    if hasattr(plant_id, "default"):
        plant_id = plant_id.default
    if hasattr(emission_factor, "default"):
        emission_factor = emission_factor.default

    carbon_results = run_carbon_scenario_analysis(plant_id=plant_id, save_artifacts=False)
    df_summary = carbon_results["sensitivity_df"]
    df_scenarios = carbon_results["weather_scenarios_df"]

    custom_calc = None
    if emission_factor is not None:
        # Load sample battery dispatch to compute custom offset
        reports_dir = ROOT_DIR / "reports"
        sample_batt_csv = reports_dir / "week4_battery_resilience.csv"
        if sample_batt_csv.exists():
            df_b = pd.read_csv(sample_batt_csv)
            # Find normal scenario or first row
            norm = df_b[df_b["scenario_name"] == "normal"]
            row = norm.iloc[0] if not norm.empty else df_b.iloc[0]
            custom_calc = calculate_carbon_offsets(
                grid_import_without_bess_kwh=float(row.get("grid_import_without_bess_mwh", 15.0) * 1000.0),
                grid_import_with_bess_kwh=float(row.get("grid_import_with_bess_mwh", 13.0) * 1000.0),
                solar_generation_kwh=float(row.get("total_solar_generation_mwh", 50.0) * 1000.0),
                solar_exported_kwh=float(row.get("total_solar_generation_mwh", 50.0) * 1000.0 * 0.3),
                grid_emission_factor=emission_factor,
            )

    return {
        "plant_id": plant_id,
        "provenance": GRID_EMISSION_PROVENANCE,
        "default_factor_kg_per_kwh": 0.716,
        "sensitivity_summary": df_summary.to_dict(orient="records"),
        "weather_scenarios_carbon": df_scenarios.to_dict(orient="records"),
        "custom_calculation": custom_calc,
    }


@app.post("/api/executive-report/generate")
def generate_executive_report_endpoint(
    plant_id: int = Query(1, ge=1, le=2, description="Plant ID (1 or 2)")
):
    """
    Regenerates the dynamic multi-page executive technical PDF report
    covering Weeks 1-4 deliverables.
    """
    if hasattr(plant_id, "default"):
        plant_id = plant_id.default
    try:
        pdf_path = generate_executive_pdf(plant_id=plant_id)
        return {
            "status": "success",
            "plant_id": plant_id,
            "filename": pdf_path.name,
            "size_kb": round(pdf_path.stat().st_size / 1024.0, 1),
            "download_url": f"/api/executive-report/download?plant_id={plant_id}",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate executive report: {str(exc)}")


@app.get("/api/executive-report/download")
def download_executive_report_endpoint(
    plant_id: int = Query(1, ge=1, le=2, description="Plant ID (1 or 2)")
):
    """
    Streams the publication-grade multi-page executive PDF report to the browser.
    """
    if hasattr(plant_id, "default"):
        plant_id = plant_id.default
    reports_dir = ROOT_DIR / "reports"
    pdf_path = reports_dir / f"executive_report_plant{plant_id}.pdf"
    if not pdf_path.exists():
        pdf_path = generate_executive_pdf(plant_id=plant_id)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"Solar_Plant_{plant_id}_Executive_Technical_Report.pdf",
    )


# Mount production React build if dist exists
dist_dir = ROOT_DIR / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")

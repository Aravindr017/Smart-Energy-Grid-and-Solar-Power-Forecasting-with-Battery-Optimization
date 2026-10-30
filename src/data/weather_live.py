"""
Live Open-Meteo Weather Forecast Integration
Fetches real-time and day-ahead meteorological data for Solar Plant 1 & 2
using configured geographic coordinates, with in-memory caching and
graceful offline fallback to historical Open-Meteo CSV datasets.
"""

import time
from typing import Dict, Any, Optional
import httpx
import pandas as pd
from pathlib import Path

from src.features.engineering import PLANT_COORDINATES
from src.data.loader import load_raw_openmeteo

# Elevation defaults matching plant sites (Gandikota = 203m, Ananthapuramu = 491m)
PLANT_ELEVATIONS = {
    1: 203.0,
    2: 491.0,
}

# In-memory weather cache: (plant_id, forecast_hours) -> (timestamp, payload)
_WEATHER_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes


def fetch_live_openmeteo_forecast(
    plant_id: int = 1,
    forecast_days: int = 2,
    timeout_seconds: float = 8.0,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Fetches live weather forecast telemetry from the Open-Meteo Weather API
    for the specified plant coordinates.

    Includes:
    - Current conditions (temperature, humidity, cloud cover, GHI, DNI, DHI, wind speed)
    - Hourly forecast variables up to `forecast_days`
    - In-memory caching with 15-minute TTL
    - Graceful fallback to historical Open-Meteo CSV if the live API is unreachable
    """
    if plant_id not in PLANT_COORDINATES:
        raise ValueError(f"Invalid plant_id: {plant_id}. Expected 1 or 2.")

    coords = PLANT_COORDINATES[plant_id]
    elevation = PLANT_ELEVATIONS.get(plant_id, 203.0)
    cache_key = f"{plant_id}_{forecast_days}"

    now = time.time()
    if not force_refresh and cache_key in _WEATHER_CACHE:
        cached_time, cached_payload = _WEATHER_CACHE[cache_key]
        if (now - cached_time) < CACHE_TTL_SECONDS:
            return cached_payload

    # Parameters for Open-Meteo API
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": coords["latitude"],
        "longitude": coords["longitude"],
        "elevation": elevation,
        "current": (
            "temperature_2m,relative_humidity_2m,cloud_cover,rain,"
            "shortwave_radiation,direct_radiation,diffuse_radiation,"
            "direct_normal_irradiance,wind_speed_10m"
        ),
        "hourly": (
            "temperature_2m,relative_humidity_2m,cloud_cover,"
            "cloud_cover_low,cloud_cover_mid,cloud_cover_high,rain,"
            "shortwave_radiation,direct_radiation,diffuse_radiation,"
            "direct_normal_irradiance,wind_speed_10m"
        ),
        "timezone": "Asia/Kolkata",
        "forecast_days": max(1, min(forecast_days, 7)),
    }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        # Parse into standardized output
        current = data.get("current", {})
        hourly = data.get("hourly", {})
        time_list = hourly.get("time", [])

        hourly_records = []
        for i, t_str in enumerate(time_list):
            hourly_records.append({
                "time": t_str,
                "temperature_2m": float(hourly.get("temperature_2m", [0.0])[i]),
                "relative_humidity_2m": float(hourly.get("relative_humidity_2m", [0.0])[i]),
                "cloud_cover": float(hourly.get("cloud_cover", [0.0])[i]),
                "cloud_cover_low": float(hourly.get("cloud_cover_low", [0.0])[i]),
                "cloud_cover_mid": float(hourly.get("cloud_cover_mid", [0.0])[i]),
                "cloud_cover_high": float(hourly.get("cloud_cover_high", [0.0])[i]),
                "rain": float(hourly.get("rain", [0.0])[i]),
                "shortwave_radiation": float(hourly.get("shortwave_radiation", [0.0])[i]),
                "direct_radiation": float(hourly.get("direct_radiation", [0.0])[i]),
                "diffuse_radiation": float(hourly.get("diffuse_radiation", [0.0])[i]),
                "direct_normal_irradiance": float(hourly.get("direct_normal_irradiance", [0.0])[i]),
                "wind_speed_10m": float(hourly.get("wind_speed_10m", [0.0])[i]),
            })

        payload = {
            "status": "online",
            "is_live": True,
            "data_source": "Live Open-Meteo Weather API",
            "plant_id": plant_id,
            "coordinates": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
                "elevation_m": elevation,
            },
            "timezone": data.get("timezone", "Asia/Kolkata"),
            "retrieved_at": pd.Timestamp.now(tz="Asia/Kolkata").strftime("%Y-%m-%d %H:%M:%S"),
            "current_conditions": {
                "time": current.get("time"),
                "temperature_c": current.get("temperature_2m"),
                "relative_humidity_pct": current.get("relative_humidity_2m"),
                "cloud_cover_pct": current.get("cloud_cover"),
                "rain_mm": current.get("rain"),
                "ghi_wm2": current.get("shortwave_radiation"),
                "direct_radiation_wm2": current.get("direct_radiation"),
                "diffuse_radiation_wm2": current.get("diffuse_radiation"),
                "dni_wm2": current.get("direct_normal_irradiance"),
                "wind_speed_kmh": current.get("wind_speed_10m"),
            },
            "total_hourly_steps": len(hourly_records),
            "hourly_forecast": hourly_records,
        }

        _WEATHER_CACHE[cache_key] = (now, payload)
        return payload

    except Exception as exc:
        # Fallback to historical Open-Meteo CSV dataset
        return _fallback_to_historical_openmeteo(plant_id, error_reason=str(exc))


def _fallback_to_historical_openmeteo(plant_id: int, error_reason: str) -> Dict[str, Any]:
    """
    Constructs an offline fallback payload using the existing historical
    Open-Meteo CSV dataset loaded via load_raw_openmeteo(plant_id).
    """
    coords = PLANT_COORDINATES.get(plant_id, {"latitude": 14.80, "longitude": 78.18})
    elevation = PLANT_ELEVATIONS.get(plant_id, 203.0)

    try:
        df_raw = load_raw_openmeteo(plant_id=plant_id)
        # Select last 48 hours for fallback horizon
        slice_df = df_raw.tail(48).copy().reset_index(drop=True)

        col_map = {
            "temperature_2m (°C)": "temperature_2m",
            "relative_humidity_2m (%)": "relative_humidity_2m",
            "cloud_cover (%)": "cloud_cover",
            "cloud_cover_low (%)": "cloud_cover_low",
            "cloud_cover_mid (%)": "cloud_cover_mid",
            "cloud_cover_high (%)": "cloud_cover_high",
            "rain (mm)": "rain",
            "shortwave_radiation (W/m²)": "shortwave_radiation",
            "direct_radiation (W/m²)": "direct_radiation",
            "diffuse_radiation (W/m²)": "diffuse_radiation",
            "direct_normal_irradiance (W/m²)": "direct_normal_irradiance",
            "wind_speed_10m (km/h)": "wind_speed_10m",
        }

        hourly_records = []
        for _, row in slice_df.iterrows():
            rec = {"time": str(row["time"])}
            for src_c, dst_c in col_map.items():
                rec[dst_c] = float(row.get(src_c, 0.0))
            hourly_records.append(rec)

        last_rec = hourly_records[-1] if hourly_records else {}
        current_cond = {
            "time": last_rec.get("time"),
            "temperature_c": last_rec.get("temperature_2m"),
            "relative_humidity_pct": last_rec.get("relative_humidity_2m"),
            "cloud_cover_pct": last_rec.get("cloud_cover"),
            "rain_mm": last_rec.get("rain"),
            "ghi_wm2": last_rec.get("shortwave_radiation"),
            "direct_radiation_wm2": last_rec.get("direct_radiation"),
            "diffuse_radiation_wm2": last_rec.get("diffuse_radiation"),
            "dni_wm2": last_rec.get("direct_normal_irradiance"),
            "wind_speed_kmh": last_rec.get("wind_speed_10m"),
        }

        return {
            "status": "fallback",
            "is_live": False,
            "data_source": "Historical Open-Meteo CSV (Offline Fallback)",
            "warning": f"Live weather API unavailable ({error_reason}). Displaying historical Open-Meteo telemetry.",
            "plant_id": plant_id,
            "coordinates": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"],
                "elevation_m": elevation,
            },
            "timezone": "Asia/Kolkata",
            "retrieved_at": pd.Timestamp.now(tz="Asia/Kolkata").strftime("%Y-%m-%d %H:%M:%S"),
            "current_conditions": current_cond,
            "total_hourly_steps": len(hourly_records),
            "hourly_forecast": hourly_records,
        }
    except Exception as inner_exc:
        return {
            "status": "error",
            "is_live": False,
            "data_source": "Unavailable",
            "error": f"Failed to retrieve weather data: {error_reason}; fallback error: {str(inner_exc)}",
            "plant_id": plant_id,
            "coordinates": coords,
            "current_conditions": {},
            "total_hourly_steps": 0,
            "hourly_forecast": [],
        }

"""
Feature Engineering Module for Solar Power Forecasting
Includes:
- Solar Zenith and Solar Elevation Angle estimation based on solar geometry
- Cyclical calendar encodings (hour of day, day of year)
- Rolling irradiance statistics (3-hour and 6-hour windows)
- Lagged generation features (t-1h, t-24h, t-48h)
- Nighttime zero-inflation handling
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple


# Coordinates for the solar plants
PLANT_COORDINATES = {
    1: {"latitude": 14.80, "longitude": 78.18},  # Plant 1 (Andhra Pradesh, India)
    2: {"latitude": 14.38, "longitude": 77.50},  # Plant 2 (Andhra Pradesh, India)
}


def calculate_solar_geometry(
    timestamps: pd.Series,
    latitude_deg: float,
    longitude_deg: float,
    tz_offset_hours: float = 5.5,
) -> Tuple[pd.Series, pd.Series]:
    """
    Computes solar elevation angle and cosine of the solar zenith angle
    using standard solar geometry equations (Spencer / NREL formulation).
    
    Args:
        timestamps: Series of pandas datetime objects (assumed local IST time).
        latitude_deg: Plant latitude in decimal degrees.
        longitude_deg: Plant longitude in decimal degrees.
        tz_offset_hours: Local timezone offset from UTC in hours (IST = +5.5).
        
    Returns:
        elevation_deg: Solar elevation angle in degrees.
        cos_zenith: Cosine of solar zenith angle (clamped to [0, 1]).
    """
    # Day of year (1-365)
    day_of_year = timestamps.dt.dayofyear.values
    time_hours = timestamps.dt.hour.values + timestamps.dt.minute.values / 60.0

    # Solar declination angle delta (degrees)
    # Cooper (1969) / Spencer equation approximation
    gamma = 2 * np.pi * (day_of_year - 1) / 365.0
    delta_deg = 23.45 * np.sin(np.radians((360.0 / 365.0) * (day_of_year - 81)))
    delta_rad = np.radians(delta_deg)

    # Equation of Time (EoT in minutes)
    eot_minutes = (
        229.18 * (0.000075 + 0.001868 * np.cos(gamma) - 0.032077 * np.sin(gamma)
                  - 0.014615 * np.cos(2 * gamma) - 0.040849 * np.sin(2 * gamma))
    )

    # Standard meridian for India (IST is based on 82.5 degrees East)
    standard_meridian = tz_offset_hours * 15.0

    # Solar Time in hours
    time_offset_hours = (4.0 * (longitude_deg - standard_meridian) + eot_minutes) / 60.0
    solar_time_hours = (time_hours + time_offset_hours) % 24.0

    # Hour angle omega (degrees): 15 deg per hour from solar noon (12:00)
    hour_angle_deg = 15.0 * (solar_time_hours - 12.0)
    hour_angle_rad = np.radians(hour_angle_deg)

    phi_rad = np.radians(latitude_deg)

    # Solar elevation angle alpha: sin(alpha) = sin(phi)*sin(delta) + cos(phi)*cos(delta)*cos(omega)
    sin_elevation = (
        np.sin(phi_rad) * np.sin(delta_rad)
        + np.cos(phi_rad) * np.cos(delta_rad) * np.cos(hour_angle_rad)
    )
    sin_elevation = np.clip(sin_elevation, -1.0, 1.0)
    elevation_deg = np.degrees(np.arcsin(sin_elevation))

    # Cosine of zenith angle is equal to sin of elevation angle
    cos_zenith = np.maximum(0.0, sin_elevation)

    return pd.Series(elevation_deg, index=timestamps.index), pd.Series(cos_zenith, index=timestamps.index)


def create_feature_pipeline(
    df: pd.DataFrame,
    plant_id: int = 1,
    target_col: str = "ac_power",
    include_lags: bool = True,
) -> pd.DataFrame:
    """
    Transforms the post-EDA handoff DataFrame into a complete ML-ready feature matrix.
    
    Engineered features:
    - Solar geometry: elevation angle, cos(zenith)
    - Cyclical temporal: sin/cos of hour and day of year
    - Rolling irradiance: 3-hour and 6-hour moving averages and std
    - Cloud composite index
    - Temperature differential
    - Target lag features: t-1h, t-24h, t-48h (if include_lags=True)
    """
    data = df.copy()
    if "time" not in data.columns:
        raise ValueError("DataFrame must contain a 'time' column.")
    
    data["time"] = pd.to_datetime(data["time"])
    data = data.sort_values("time").reset_index(drop=True)

    coords = PLANT_COORDINATES.get(plant_id, {"latitude": 14.80, "longitude": 78.18})
    elevation, cos_zenith = calculate_solar_geometry(
        data["time"],
        latitude_deg=coords["latitude"],
        longitude_deg=coords["longitude"],
    )
    data["solar_elevation_deg"] = elevation
    data["cos_zenith"] = cos_zenith

    # Cyclical hour encoding (24-hour cycle)
    hour = data["time"].dt.hour + data["time"].dt.minute / 60.0
    data["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    data["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)

    # Cyclical day-of-year encoding
    day = data["time"].dt.dayofyear
    data["day_sin"] = np.sin(2 * np.pi * day / 365.25)
    data["day_cos"] = np.cos(2 * np.pi * day / 365.25)

    # Cloud composite index
    cloud_cols = [c for c in ["cloud", "cloud_low", "cloud_mid", "cloud_high"] if c in data.columns]
    if cloud_cols:
        data["cloud_cover_index"] = data[cloud_cols].mean(axis=1)

    # Temperature differential (module temperature minus ambient)
    if "module_temperature" in data.columns and "sensor_temperature" in data.columns:
        data["temp_diff_module_sensor"] = data["module_temperature"] - data["sensor_temperature"]

    # Rolling solar irradiance statistics (causal / backward-looking)
    if "ghi" in data.columns:
        data["ghi_rolling_mean_3h"] = data["ghi"].rolling(window=3, min_periods=1).mean()
        data["ghi_rolling_std_3h"] = data["ghi"].rolling(window=3, min_periods=1).std().fillna(0.0)
        data["ghi_rolling_mean_6h"] = data["ghi"].rolling(window=6, min_periods=1).mean()

    if "sensor_irradiation" in data.columns:
        data["irrad_rolling_mean_3h"] = data["sensor_irradiation"].rolling(window=3, min_periods=1).mean()

    # Target lag features (for baseline and autoregressive models)
    if include_lags and target_col in data.columns:
        data[f"{target_col}_lag_1h"] = data[target_col].shift(1)
        data[f"{target_col}_lag_24h"] = data[target_col].shift(24)
        data[f"{target_col}_lag_48h"] = data[target_col].shift(48)
        
        # 24h rolling max generation
        data[f"{target_col}_rolling_max_24h"] = (
            data[target_col].shift(1).rolling(window=24, min_periods=1).max()
        )

    # Daylight indicator (Boolean mask)
    # Solar generation occurs strictly when elevation > 0 and irradiance > 0
    is_daylight = (data["solar_elevation_deg"] > 0)
    if "ghi" in data.columns:
        is_daylight = is_daylight & (data["ghi"] > 0)
    data["is_daylight"] = is_daylight

    return data


def apply_nighttime_zero_inflation(
    predictions: np.ndarray,
    df_features: pd.DataFrame,
    elevation_threshold: float = 0.0,
    ghi_threshold: float = 1.0,
) -> np.ndarray:
    """
    Enforces strictly zero generation during nighttime hours to eliminate
    phantom predictions, small negative values, and nighttime leakage.
    
    Args:
        predictions: Array of forecasted AC power values.
        df_features: DataFrame containing 'solar_elevation_deg' and/or 'ghi'.
        elevation_threshold: Solar elevation cutoff in degrees.
        ghi_threshold: Global Horizontal Irradiance cutoff in W/m².
        
    Returns:
        Post-processed predictions with night hours clamped to exactly 0.0 kW.
    """
    preds = np.asarray(predictions, dtype=float).copy()
    
    # Clip any negative daytime predictions to 0
    preds = np.maximum(0.0, preds)
    
    # Identify night mask
    night_mask = np.zeros(len(preds), dtype=bool)
    if "solar_elevation_deg" in df_features.columns:
        night_mask |= (df_features["solar_elevation_deg"].values <= elevation_threshold)
    if "ghi" in df_features.columns:
        night_mask |= (df_features["ghi"].values <= ghi_threshold)
    elif "cos_zenith" in df_features.columns:
        night_mask |= (df_features["cos_zenith"].values <= 0.0)

    preds[night_mask] = 0.0
    return preds

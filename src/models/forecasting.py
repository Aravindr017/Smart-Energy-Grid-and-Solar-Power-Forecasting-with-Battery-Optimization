"""
Advanced Forecasting Models for Solar Power Generation (Week 2 AI/ML Deliverable)
Includes:
- LightGBM Gradient Boosted Decision Trees Forecaster (tabular weather + solar geometry + lags)
- Facebook Prophet Forecaster (additive time-series decomposition with exogenous weather regressors)
- Integrated Week 2 Evaluation Pipeline benchmarking Baselines vs LightGBM vs Prophet
"""

import logging
import warnings
from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
import pandas as pd
import lightgbm as lgb
import xgboost as xgb
from prophet import Prophet

from src.features.engineering import create_feature_pipeline, apply_nighttime_zero_inflation
from src.models.baseline import temporal_train_test_split, Persistence24hModel, LinearBaselinePipeline
from src.models.metrics import evaluate_forecast

# Suppress Prophet / cmdstanpy verbose logs
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=FutureWarning)


class LightGBMForecaster:
    """
    LightGBM Gradient Boosted Decision Tree Regressor for Solar Power Forecasting.

    Optimized for high-throughput tabular solar data with nonlinear solar geometry,
    sensor weather interactions, cyclical calendar features, and autoregressive lags.
    """
    def __init__(
        self,
        feature_cols: Optional[List[str]] = None,
        target_col: str = "ac_power",
        n_estimators: int = 300,
        learning_rate: float = 0.03,
        num_leaves: int = 31,
        max_depth: int = 6,
        subsample: float = 0.85,
        colsample_bytree: float = 0.85,
        random_state: int = 42,
    ):
        self.feature_cols = feature_cols
        self.target_col = target_col
        self.params = {
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "num_leaves": num_leaves,
            "max_depth": max_depth,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": random_state,
            "n_jobs": -1,
            "verbose": -1,
            "objective": "regression",
        }
        self.model = lgb.LGBMRegressor(**self.params)
        self.is_fitted: bool = False
        self.fitted_features_: List[str] = []

    def fit(self, train_df: pd.DataFrame) -> "LightGBMForecaster":
        """Fits the LightGBM model on training data."""
        if self.feature_cols is None:
            # Candidate features
            candidates = [
                "cos_zenith",
                "solar_elevation_deg",
                "hour_sin",
                "hour_cos",
                "day_sin",
                "day_cos",
                "inverter_code",
                "openmeteo_temperature",
                "humidity",
                "ghi",
                "direct_radiation",
                "dhi",
                "cloud_cover_index",
                "temp_diff_module_sensor",
                "ghi_rolling_mean_3h",
                "ghi_rolling_mean_6h",
                "ac_power_lag_1step",
                "ac_power_lag_1h",
                "ac_power_lag_24h",
            ]
            self.fitted_features_ = [c for c in candidates if c in train_df.columns]
        else:
            self.fitted_features_ = [c for c in self.feature_cols if c in train_df.columns]

        clean_train = train_df.dropna(subset=self.fitted_features_ + [self.target_col])
        X = clean_train[self.fitted_features_]
        y = clean_train[self.target_col]

        # Categorical feature specification if present
        cat_features = ["inverter_code"] if "inverter_code" in self.fitted_features_ else []

        self.model.fit(
            X,
            y,
            categorical_feature=cat_features if cat_features else "auto",
        )
        self.is_fitted = True
        return self

    def predict(self, test_df: pd.DataFrame, enforce_night_zero: bool = True) -> np.ndarray:
        """
        Generates predictions for test_df and applies physical zero-inflation.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict() is called.")

        X = test_df[self.fitted_features_].fillna(0.0)
        raw_preds = self.model.predict(X)
        raw_preds = np.maximum(0.0, raw_preds)

        if enforce_night_zero:
            return apply_nighttime_zero_inflation(raw_preds, test_df)
        return raw_preds

    def get_feature_importances(self) -> pd.DataFrame:
        """Returns sorted feature importances (gain and split counts)."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before retrieving feature importances.")

        return pd.DataFrame({
            "feature": self.fitted_features_,
            "importance": self.model.feature_importances_
        }).sort_values("importance", ascending=False).reset_index(drop=True)


class XGBoostForecaster:
    """
    XGBoost Gradient Boosted Decision Tree Regressor for Solar Power Forecasting.
    Evaluates alongside LightGBM and Prophet on chronological train/test data.
    """
    def __init__(
        self,
        feature_cols: Optional[List[str]] = None,
        target_col: str = "ac_power",
        n_estimators: int = 300,
        learning_rate: float = 0.03,
        max_depth: int = 6,
        subsample: float = 0.85,
        colsample_bytree: float = 0.85,
        random_state: int = 42,
    ):
        self.feature_cols = feature_cols
        self.target_col = target_col
        self.params = {
            "n_estimators": n_estimators,
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "random_state": random_state,
            "n_jobs": -1,
            "verbosity": 0,
            "objective": "reg:squarederror",
        }
        self.model = xgb.XGBRegressor(**self.params)
        self.is_fitted: bool = False
        self.fitted_features_: List[str] = []

    def fit(self, train_df: pd.DataFrame) -> "XGBoostForecaster":
        """Fits the XGBoost model on training data."""
        if self.feature_cols is None:
            candidates = [
                "cos_zenith",
                "solar_elevation_deg",
                "hour_sin",
                "hour_cos",
                "day_sin",
                "day_cos",
                "inverter_code",
                "openmeteo_temperature",
                "humidity",
                "ghi",
                "direct_radiation",
                "dhi",
                "cloud_cover_index",
                "temp_diff_module_sensor",
                "ghi_rolling_mean_3h",
                "ghi_rolling_mean_6h",
                "ac_power_lag_1step",
                "ac_power_lag_1h",
                "ac_power_lag_24h",
            ]
            self.fitted_features_ = [c for c in candidates if c in train_df.columns]
        else:
            self.fitted_features_ = [c for c in self.feature_cols if c in train_df.columns]

        clean_train = train_df.dropna(subset=self.fitted_features_ + [self.target_col])
        X = clean_train[self.fitted_features_]
        y = clean_train[self.target_col]

        self.model.fit(X, y)
        self.is_fitted = True
        return self

    def predict(self, test_df: pd.DataFrame, enforce_night_zero: bool = True) -> np.ndarray:
        """Generates predictions for test_df and applies physical zero-inflation."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict() is called.")

        X = test_df[self.fitted_features_].fillna(0.0)
        raw_preds = self.model.predict(X)
        raw_preds = np.maximum(0.0, raw_preds)

        if enforce_night_zero:
            return apply_nighttime_zero_inflation(raw_preds, test_df)
        return raw_preds

    def get_feature_importances(self) -> pd.DataFrame:
        """Returns sorted feature importances."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before retrieving feature importances.")
        return pd.DataFrame({
            "feature": self.fitted_features_,
            "importance": self.model.feature_importances_
        }).sort_values("importance", ascending=False).reset_index(drop=True)



class ProphetForecaster:
    """
    Facebook Prophet Time-Series Forecaster.

    Decomposes solar generation into trend + daily diurnal seasonality
    augmented by key exogenous meteorological regressors (GHI, temperature, zenith).
    Operates on plant-level or single-inverter continuous chronological sequences.
    """
    def __init__(
        self,
        time_col: str = "time",
        target_col: str = "ac_power",
        regressors: Optional[List[str]] = None,
        daily_seasonality: bool = True,
        weekly_seasonality: bool = False,
    ):
        self.time_col = time_col
        self.target_col = target_col
        self.regressors = regressors if regressors is not None else ["ghi", "openmeteo_temperature", "cos_zenith"]
        self.daily_seasonality = daily_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.model: Optional[Prophet] = None
        self.active_regressors_: List[str] = []

    def _prepare_prophet_df(self, df: pd.DataFrame) -> pd.DataFrame:
        pdf = pd.DataFrame()
        pdf["ds"] = pd.to_datetime(df[self.time_col])
        if self.target_col in df.columns:
            pdf["y"] = df[self.target_col].values
        for r in self.active_regressors_:
            if r in df.columns:
                pdf[r] = df[r].fillna(0.0).values
            else:
                pdf[r] = 0.0
        return pdf

    def fit(self, train_df: pd.DataFrame) -> "ProphetForecaster":
        """Fits the Prophet model with exogenous regressors."""
        self.active_regressors_ = [r for r in self.regressors if r in train_df.columns]

        self.model = Prophet(
            daily_seasonality=self.daily_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            yearly_seasonality=False,
            changepoint_prior_scale=0.05,
        )

        for reg in self.active_regressors_:
            self.model.add_regressor(reg)

        prophet_train = self._prepare_prophet_df(train_df).dropna(subset=["ds", "y"])
        # Prophet handles timezone-naive timestamps
        if prophet_train["ds"].dt.tz is not None:
            prophet_train["ds"] = prophet_train["ds"].dt.tz_localize(None)

        self.model.fit(prophet_train)
        return self

    def predict(self, test_df: pd.DataFrame, enforce_night_zero: bool = True) -> np.ndarray:
        """Forecasts AC power and applies nighttime zero-inflation."""
        if self.model is None:
            raise RuntimeError("Prophet model must be fitted before predict() is called.")

        prophet_test = self._prepare_prophet_df(test_df)
        if prophet_test["ds"].dt.tz is not None:
            prophet_test["ds"] = prophet_test["ds"].dt.tz_localize(None)

        forecast = self.model.predict(prophet_test)
        raw_preds = np.maximum(0.0, forecast["yhat"].values)

        if enforce_night_zero:
            return apply_nighttime_zero_inflation(raw_preds, test_df)
        return raw_preds


def run_week2_forecasting_benchmark(
    df_raw: pd.DataFrame,
    plant_id: int = 1,
    test_days: int = 7,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, np.ndarray], pd.DataFrame]:
    """
    Executes the comprehensive Week 2 AI/ML forecasting benchmark:
    - Feature engineering (lags, solar geometry, rolling weather stats)
    - Chronological train/test split (last 7 days out-of-sample)
    - Benchmarks:
      1. Persistence (24h Lag) [Naive Benchmark]
      2. Ridge Regression Baseline [Week 1]
      3. Prophet Forecaster [Week 2 Additive Time Series]
      4. LightGBM Forecaster [Week 2 Gradient Boosting Trees]
    - Evaluation across Daylight RMSE, Daylight MAPE, Daylight R², Overall RMSE, nRMSE.

    Returns:
        metrics_df: Comparison leaderboard of all evaluated models
        test_df: Test slice DataFrame
        predictions_dict: Dictionary of model predictions on the test set
        feature_importance_df: LightGBM feature importance rankings
    """
    # 1. Feature Engineering
    df_feat = create_feature_pipeline(
        df_raw,
        plant_id=plant_id,
        target_col="ac_power",
        include_lags=True,
    )

    # 2. Chronological Split
    train_df, test_df = temporal_train_test_split(df_feat, test_days=test_days)

    predictions_dict = {}

    # Model 1: Persistence Benchmark (same time yesterday)
    p24 = Persistence24hModel(target_col="ac_power")
    p24_preds = apply_nighttime_zero_inflation(p24.predict(test_df), test_df)
    predictions_dict["Persistence (24h Lag)"] = p24_preds

    # Model 2: Ridge Regression Baseline (Week 1 Champion)
    feature_cols = [
        "cos_zenith",
        "solar_elevation_deg",
        "hour_sin",
        "hour_cos",
        "inverter_code",
        "openmeteo_temperature",
        "humidity",
        "ghi",
        "direct_radiation",
        "dhi",
        "cloud_cover_index",
        "ghi_rolling_mean_3h",
        "ac_power_lag_1step",
        "ac_power_lag_1h",
        "ac_power_lag_24h",
    ]
    avail_cols = [c for c in feature_cols if c in df_feat.columns]

    ridge = LinearBaselinePipeline(
        feature_cols=avail_cols,
        target_col="ac_power",
        model_type="ridge",
        alpha=10.0,
    ).fit(train_df)
    predictions_dict["Ridge Regression (Baseline)"] = ridge.predict(test_df, enforce_night_zero=True)

    # Model 3: Facebook Prophet
    prophet_model = ProphetForecaster(
        time_col="time",
        target_col="ac_power",
        regressors=["ghi", "openmeteo_temperature", "cos_zenith"],
    )
    # For multi-inverter data, Prophet operates cleanly on aggregated or per-timestamp basis;
    # if inverter-level, fit on mean profile or group
    if "source_key" in train_df.columns and train_df["source_key"].nunique() > 1:
        # Train plant-level prophet and scale proportionally per inverter
        train_agg = train_df.groupby("time").agg({
            "ac_power": "sum",
            "ghi": "first",
            "openmeteo_temperature": "first",
            "cos_zenith": "first",
            "solar_elevation_deg": "first",
        }).reset_index()
        prophet_model.fit(train_agg)

        test_agg = test_df.groupby("time").agg({
            "ghi": "first",
            "openmeteo_temperature": "first",
            "cos_zenith": "first",
            "solar_elevation_deg": "first",
        }).reset_index()
        prophet_agg_preds = prophet_model.predict(test_agg, enforce_night_zero=True)
        # Map aggregated prediction back divided by number of inverters (22)
        n_inverters = train_df["source_key"].nunique()
        time_to_pred = dict(zip(test_agg["time"], prophet_agg_preds / n_inverters))
        prophet_preds = test_df["time"].map(time_to_pred).fillna(0.0).values
        prophet_preds = apply_nighttime_zero_inflation(prophet_preds, test_df)
    else:
        prophet_model.fit(train_df)
        prophet_preds = prophet_model.predict(test_df, enforce_night_zero=True)

    predictions_dict["Prophet (Additive TS)"] = prophet_preds

    # Model 4: LightGBM Gradient Boosted Trees (Week 2 Hero)
    lgb_model = LightGBMForecaster(
        feature_cols=avail_cols,
        target_col="ac_power",
        n_estimators=300,
        learning_rate=0.03,
        num_leaves=31,
    ).fit(train_df)
    lgb_preds = lgb_model.predict(test_df, enforce_night_zero=True)
    predictions_dict["LightGBM (GBDT)"] = lgb_preds
    feat_imp = lgb_model.get_feature_importances()

    # Model 5: XGBoost Gradient Boosted Trees (Comparison requirement)
    xgb_model = XGBoostForecaster(
        feature_cols=avail_cols,
        target_col="ac_power",
        n_estimators=300,
        learning_rate=0.03,
        max_depth=6,
    ).fit(train_df)
    xgb_preds = xgb_model.predict(test_df, enforce_night_zero=True)
    predictions_dict["XGBoost (GBDT)"] = xgb_preds

    # 3. Evaluate Metrics
    y_test = test_df["ac_power"].values
    is_daylight = test_df["is_daylight"].values

    metrics_list = []
    for model_name, preds in predictions_dict.items():
        m = evaluate_forecast(y_test, preds, is_daylight=is_daylight)
        m["model"] = model_name
        m["plant_id"] = plant_id
        metrics_list.append(m)

    metrics_df = pd.DataFrame(metrics_list)
    cols_order = [
        "model", "daylight_rmse", "daylight_mape_pct", "daylight_mae", "daylight_r2",
        "rmse_overall", "mae_overall", "r2_overall", "daylight_nrmse_pct"
    ]
    metrics_df = metrics_df[[c for c in cols_order if c in metrics_df.columns]]
    metrics_df = metrics_df.sort_values("daylight_rmse").reset_index(drop=True)

    return metrics_df, test_df, predictions_dict, feat_imp


# -----------------------------------------------------------------------------
# Genuine 24-Hour Ahead Solar Forecasting Engine (Operational Day-Ahead)
# -----------------------------------------------------------------------------
_DAY_AHEAD_MODEL_CACHE: Dict[int, Dict[str, Any]] = {}


def _get_or_train_day_ahead_models(plant_id: int) -> Dict[str, Any]:
    """
    Fits and caches plant-level weather-driven models (LightGBM, XGBoost, Prophet)
    trained strictly on historical hourly telemetry and solar geometry.
    These models do NOT require autoregressive lags of future power.
    """
    if plant_id in _DAY_AHEAD_MODEL_CACHE:
        return _DAY_AHEAD_MODEL_CACHE[plant_id]

    from src.data.loader import load_processed_handoff
    from src.features.engineering import PLANT_COORDINATES, calculate_solar_geometry

    coords = PLANT_COORDINATES.get(plant_id, {"latitude": 14.80, "longitude": 78.18})
    df_hist = load_processed_handoff(plant_id=plant_id, freq="hourly").copy()

    elev, cos_z = calculate_solar_geometry(df_hist["time"], coords["latitude"], coords["longitude"])
    df_hist["cos_zenith"] = cos_z
    df_hist["solar_elevation_deg"] = elev

    hour = df_hist["time"].dt.hour
    df_hist["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    df_hist["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    day = df_hist["time"].dt.dayofyear
    df_hist["day_sin"] = np.sin(2 * np.pi * day / 365.25)
    df_hist["day_cos"] = np.cos(2 * np.pi * day / 365.25)

    cloud_cols = [c for c in ["cloud", "cloud_low", "cloud_mid", "cloud_high"] if c in df_hist.columns]
    df_hist["cloud_cover_index"] = df_hist[cloud_cols].mean(axis=1) if cloud_cols else 0.0
    df_hist["ghi_rolling_mean_3h"] = df_hist["ghi"].rolling(3, min_periods=1).mean()

    weather_features = [
        "cos_zenith", "solar_elevation_deg", "hour_sin", "hour_cos", "day_sin", "day_cos",
        "openmeteo_temperature", "humidity", "ghi", "direct_radiation", "dhi",
        "cloud_cover_index", "ghi_rolling_mean_3h"
    ]

    clean = df_hist.dropna(subset=weather_features + ["ac_power"])
    X_train = clean[weather_features]
    y_train = clean["ac_power"]

    # 1. LightGBM
    lgb_m = lgb.LGBMRegressor(
        n_estimators=160,
        learning_rate=0.04,
        num_leaves=31,
        max_depth=6,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        verbose=-1
    )
    lgb_m.fit(X_train, y_train)

    # 2. XGBoost
    xgb_m = xgb.XGBRegressor(
        n_estimators=160,
        learning_rate=0.04,
        max_depth=5,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        verbosity=0
    )
    xgb_m.fit(X_train, y_train)

    # 3. Prophet
    prophet_m = ProphetForecaster(
        time_col="time",
        target_col="ac_power",
        regressors=["ghi", "openmeteo_temperature", "cos_zenith"],
    )
    prophet_m.fit(clean)

    # Calculate empirical residual standard deviation during daytime for uncertainty bounds
    train_preds = lgb_m.predict(X_train)
    daytime_mask = clean["ghi"].values > 20.0
    resids = y_train.values[daytime_mask] - train_preds[daytime_mask]
    residual_std = float(np.std(resids)) if len(resids) > 0 else 1200.0

    cache_obj = {
        "features": weather_features,
        "lgb": lgb_m,
        "xgb": xgb_m,
        "prophet": prophet_m,
        "residual_std": residual_std,
    }
    _DAY_AHEAD_MODEL_CACHE[plant_id] = cache_obj
    return cache_obj


def generate_24h_ahead_solar_forecast(
    plant_id: int = 1,
    live_weather_payload: Optional[Dict[str, Any]] = None,
    horizon_hours: int = 24,
) -> Dict[str, Any]:
    """
    Generates genuine 24-hour ahead solar power forecasting using live Open-Meteo
    weather forecast variables, solar geometry, and pre-trained GBDT/Prophet models.

    Preserves:
    - Correct localized timestamps
    - Non-negative outputs
    - Nighttime zero-inflation
    - 90% confidence prediction intervals
    """
    from src.features.engineering import PLANT_COORDINATES, calculate_solar_geometry
    from src.data.weather_live import fetch_live_openmeteo_forecast

    coords = PLANT_COORDINATES.get(plant_id, {"latitude": 14.80, "longitude": 78.18})

    if live_weather_payload is None:
        live_weather_payload = fetch_live_openmeteo_forecast(plant_id=plant_id, forecast_days=2)

    hourly_records = live_weather_payload.get("hourly_forecast", [])
    if not hourly_records:
        raise ValueError(f"No hourly weather forecast records available for Plant {plant_id}")

    df_weather = pd.DataFrame(hourly_records)
    df_weather["time"] = pd.to_datetime(df_weather["time"])
    df_weather = df_weather.sort_values("time").reset_index(drop=True)

    # Select upcoming horizon_hours starting from current local hour
    now_ist = pd.Timestamp.now(tz="Asia/Kolkata").tz_localize(None)
    future_mask = df_weather["time"] >= (now_ist.floor("h"))
    df_horizon = df_weather[future_mask].head(horizon_hours).copy()
    if len(df_horizon) < horizon_hours:
        df_horizon = df_weather.head(horizon_hours).copy()

    df_horizon = df_horizon.reset_index(drop=True)

    # Compute solar geometry for future timestamps
    elev, cos_z = calculate_solar_geometry(df_horizon["time"], coords["latitude"], coords["longitude"])
    df_horizon["cos_zenith"] = cos_z
    df_horizon["solar_elevation_deg"] = elev

    hour = df_horizon["time"].dt.hour + df_horizon["time"].dt.minute / 60.0
    df_horizon["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    df_horizon["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    day = df_horizon["time"].dt.dayofyear
    df_horizon["day_sin"] = np.sin(2 * np.pi * day / 365.25)
    df_horizon["day_cos"] = np.cos(2 * np.pi * day / 365.25)

    df_horizon["openmeteo_temperature"] = df_horizon["temperature_2m"]
    df_horizon["humidity"] = df_horizon["relative_humidity_2m"]
    df_horizon["ghi"] = df_horizon["shortwave_radiation"]
    df_horizon["dhi"] = df_horizon["diffuse_radiation"]
    df_horizon["dni"] = df_horizon["direct_normal_irradiance"]
    df_horizon["cloud"] = df_horizon["cloud_cover"]
    df_horizon["cloud_low"] = df_horizon["cloud_cover_low"]
    df_horizon["cloud_mid"] = df_horizon["cloud_cover_mid"]
    df_horizon["cloud_high"] = df_horizon["cloud_cover_high"]
    df_horizon["cloud_cover_index"] = df_horizon[["cloud", "cloud_low", "cloud_mid", "cloud_high"]].mean(axis=1)
    df_horizon["ghi_rolling_mean_3h"] = df_horizon["ghi"].rolling(3, min_periods=1).mean()

    # Load / train day-ahead models
    models = _get_or_train_day_ahead_models(plant_id)
    features = models["features"]

    X_fut = df_horizon[features].fillna(0.0)

    # Predictions
    raw_lgb = models["lgb"].predict(X_fut)
    raw_xgb = models["xgb"].predict(X_fut)
    raw_prophet = models["prophet"].predict(df_horizon, enforce_night_zero=False)

    pred_lgb = apply_nighttime_zero_inflation(np.maximum(0.0, raw_lgb), df_horizon)
    pred_xgb = apply_nighttime_zero_inflation(np.maximum(0.0, raw_xgb), df_horizon)
    pred_prophet = apply_nighttime_zero_inflation(np.maximum(0.0, raw_prophet), df_horizon)

    # Primary selected prediction: LightGBM (Week 2 Champion)
    selected_pred = pred_lgb.copy()

    # 90% Prediction Interval Bounds
    r_std = models["residual_std"]
    lower_bound = np.maximum(0.0, selected_pred - 1.645 * r_std)
    upper_bound = np.maximum(lower_bound, selected_pred + 1.645 * r_std)

    # Clamp bounds to zero during nighttime
    night_mask = (df_horizon["cos_zenith"].values <= 0.0) | (df_horizon["ghi"].values <= 1.0)
    lower_bound[night_mask] = 0.0
    upper_bound[night_mask] = 0.0

    timeline = []
    for i, row in df_horizon.iterrows():
        t_dt = row["time"]
        timeline.append({
            "timestamp": t_dt.strftime("%Y-%m-%d %H:%M"),
            "time_label": t_dt.strftime("%H:%M"),
            "hour_int": int(t_dt.hour),
            "lightgbm_kw": round(float(pred_lgb[i]), 1),
            "xgboost_kw": round(float(pred_xgb[i]), 1),
            "prophet_kw": round(float(pred_prophet[i]), 1),
            "selected_solar_kw": round(float(selected_pred[i]), 1),
            "lower_bound_kw": round(float(lower_bound[i]), 1),
            "upper_bound_kw": round(float(upper_bound[i]), 1),
            "ghi_wm2": round(float(row["ghi"]), 1),
            "ambient_temp_c": round(float(row["openmeteo_temperature"]), 1),
            "cloud_cover_pct": round(float(row["cloud_cover_index"]), 1),
            "wind_speed_kmh": round(float(row.get("wind_speed_10m", 0.0)), 1),
            "is_daylight": bool(not night_mask[i]),
        })

    total_mwh = float(selected_pred.sum() / 1000.0)
    peak_kw = float(selected_pred.max())

    return {
        "status": "success",
        "plant_id": plant_id,
        "is_future_forecast": True,
        "forecast_type": "24-Hour Ahead Solar Generation Forecast",
        "is_live_weather": live_weather_payload.get("is_live", False),
        "data_source": live_weather_payload.get("data_source", "Open-Meteo Weather API"),
        "retrieved_at": live_weather_payload.get("retrieved_at"),
        "forecast_horizon_hours": len(timeline),
        "forecast_start": df_horizon["time"].iloc[0].strftime("%Y-%m-%d %H:%M"),
        "forecast_end": df_horizon["time"].iloc[-1].strftime("%Y-%m-%d %H:%M"),
        "model_champion": "LightGBM (GBDT)",
        "models_evaluated": ["LightGBM (GBDT)", "XGBoost (GBDT)", "Facebook Prophet"],
        "kpis": {
            "total_predicted_energy_mwh": round(total_mwh, 2),
            "peak_predicted_kw": round(peak_kw, 1),
            "daylight_hours": int((~night_mask).sum()),
        },
        "bounds_info": {
            "confidence_level": "90%",
            "std_error_kw": round(r_std, 1),
            "methodology": "Empirical residual standard error envelope with physical zero floor",
        },
        "timeline": timeline,
    }

"""
Baseline Models for Solar Power Forecasting (Week 1 AI/ML Deliverable)
Includes:
- Chronological Time-Based Split (strict sequential split without leakage)
- 24-Hour Persistence Benchmark (yesterday's power at the same hour)
- Climatological Diurnal Mean Benchmark
- Linear Regression & Ridge Regression Baselines with Nighttime Zero-Inflation
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, List, Optional
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from src.features.engineering import create_feature_pipeline, apply_nighttime_zero_inflation
from src.models.metrics import evaluate_forecast


def temporal_train_test_split(
    df: pd.DataFrame,
    test_days: int = 7,
    time_col: str = "time",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Performs a strict chronological train/test split.
    The final `test_days` (default: 7 days = 168 hours for hourly resolution)
    form the out-of-sample evaluation test set.
    """
    data = df.sort_values(time_col).reset_index(drop=True)
    max_time = data[time_col].max()
    cutoff_time = max_time - pd.Timedelta(days=test_days)

    train_df = data[data[time_col] <= cutoff_time].copy()
    test_df = data[data[time_col] > cutoff_time].copy()

    return train_df, test_df


class Persistence24hModel:
    """
    24-Hour Lag Persistence Benchmark.
    Predicts solar power at time t using the actual observed power at t - 24 hours.
    Standard industrial baseline for day-ahead solar forecasting.
    """
    def __init__(self, target_col: str = "ac_power"):
        self.target_col = target_col

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        lag_col = f"{self.target_col}_lag_24h"
        if lag_col in df.columns:
            preds = df[lag_col].fillna(0.0).values
        else:
            preds = df[self.target_col].shift(24).fillna(0.0).values
        return np.maximum(0.0, preds)


class DiurnalMeanModel:
    """
    Historical Climatological Mean Benchmark.
    Predicts the mean daytime generation for each daily time slot (and per inverter if source_key is present).
    """
    def __init__(self, target_col: str = "ac_power"):
        self.target_col = target_col
        self.means: Dict = {}
        self.global_means: Dict = {}
        self.has_source_key: bool = False

    def fit(self, train_df: pd.DataFrame) -> "DiurnalMeanModel":
        train_copy = train_df.copy()
        time_series = pd.to_datetime(train_copy["time"])
        train_copy["time_slot"] = time_series.dt.hour * 60 + time_series.dt.minute
        self.has_source_key = "source_key" in train_copy.columns
        if self.has_source_key:
            self.means = train_copy.groupby(["source_key", "time_slot"])[self.target_col].mean().to_dict()
            self.global_means = train_copy.groupby("time_slot")[self.target_col].mean().to_dict()
        else:
            self.means = train_copy.groupby("time_slot")[self.target_col].mean().to_dict()
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        time_series = pd.to_datetime(df["time"])
        slots = time_series.dt.hour * 60 + time_series.dt.minute
        if self.has_source_key and "source_key" in df.columns:
            keys = list(zip(df["source_key"], slots))
            preds = np.array([self.means.get(k, self.global_means.get(k[1], 0.0)) for k in keys])
        else:
            preds = slots.map(self.means).fillna(0.0).values
        return np.maximum(0.0, preds)


class LinearBaselinePipeline:
    """
    Standardized Linear / Ridge Regression Baseline with Feature Scaling
    and Nighttime Zero-Inflation Enforcement.
    """
    def __init__(
        self,
        feature_cols: List[str],
        target_col: str = "ac_power",
        model_type: str = "ridge",
        alpha: float = 1.0,
    ):
        self.feature_cols = feature_cols
        self.target_col = target_col
        self.model_type = model_type
        self.alpha = alpha
        
        regressor = Ridge(alpha=alpha) if model_type == "ridge" else LinearRegression()
        self.pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("regressor", regressor)
        ])

    def fit(self, train_df: pd.DataFrame) -> "LinearBaselinePipeline":
        clean_train = train_df.dropna(subset=self.feature_cols + [self.target_col])
        X = clean_train[self.feature_cols]
        y = clean_train[self.target_col]
        self.pipeline.fit(X, y)
        return self

    def predict(self, test_df: pd.DataFrame, enforce_night_zero: bool = True) -> np.ndarray:
        X = test_df[self.feature_cols].fillna(0.0)
        raw_preds = self.pipeline.predict(X)
        if enforce_night_zero:
            return apply_nighttime_zero_inflation(raw_preds, test_df)
        return np.maximum(0.0, raw_preds)


def run_week1_baseline_benchmark(
    df_raw: pd.DataFrame,
    plant_id: int = 1,
    test_days: int = 7,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, np.ndarray]]:
    """
    Executes the complete Week 1 AI/ML benchmark pipeline:
    1. Feature engineering (solar zenith, rolling stats, lags, inverter encoding)
    2. Chronological train/test split (last 7 days test)
    3. Benchmarking 4 models:
       - Persistence 24h
       - Diurnal Mean
       - Linear Regression
       - Ridge Regression
    4. Evaluating Daylight RMSE, Daylight MAPE, and Overall RMSE
    
    Returns:
        metrics_df: Comparison table of all baseline models
        test_df: Out-of-sample test DataFrame with timestamps and actuals
        predictions_dict: Dictionary mapping model name to test predictions
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
    # Filter features to those actually present in DataFrame
    available_features = [f for f in feature_cols if f in df_feat.columns]

    predictions_dict = {}

    # Model 1: Persistence 24h (same time yesterday)
    p24_model = Persistence24hModel(target_col="ac_power")
    p24_preds = p24_model.predict(test_df)
    p24_preds = apply_nighttime_zero_inflation(p24_preds, test_df)
    predictions_dict["Persistence (24h Lag)"] = p24_preds

    # Model 2: Diurnal Time Slot Mean
    mean_model = DiurnalMeanModel(target_col="ac_power").fit(train_df)
    mean_preds = mean_model.predict(test_df)
    mean_preds = apply_nighttime_zero_inflation(mean_preds, test_df)
    predictions_dict["Diurnal Mean"] = mean_preds

    # Model 3: Linear Regression Baseline
    lin_model = LinearBaselinePipeline(
        feature_cols=available_features,
        target_col="ac_power",
        model_type="linear",
    ).fit(train_df)
    lin_preds = lin_model.predict(test_df, enforce_night_zero=True)
    predictions_dict["Linear Regression"] = lin_preds

    # Model 4: Ridge Regression Baseline
    ridge_model = LinearBaselinePipeline(
        feature_cols=available_features,
        target_col="ac_power",
        model_type="ridge",
        alpha=10.0,
    ).fit(train_df)
    ridge_preds = ridge_model.predict(test_df, enforce_night_zero=True)
    predictions_dict["Ridge Regression"] = ridge_preds

    # 3. Evaluate Metrics for all models
    y_test = test_df["ac_power"].values
    is_daylight = test_df["is_daylight"].values

    metrics_list = []
    for model_name, preds in predictions_dict.items():
        m = evaluate_forecast(y_test, preds, is_daylight=is_daylight)
        m["model"] = model_name
        m["plant_id"] = plant_id
        metrics_list.append(m)

    metrics_df = pd.DataFrame(metrics_list)
    # Reorder columns for readability
    cols_order = [
        "model", "daylight_rmse", "daylight_mape_pct", "daylight_mae", "daylight_r2",
        "rmse_overall", "mae_overall", "r2_overall", "daylight_nrmse_pct"
    ]
    metrics_df = metrics_df[[c for c in cols_order if c in metrics_df.columns]]
    metrics_df = metrics_df.sort_values("daylight_rmse").reset_index(drop=True)

    return metrics_df, test_df, predictions_dict

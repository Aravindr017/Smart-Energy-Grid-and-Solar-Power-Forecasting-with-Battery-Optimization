"""
Advanced Forecasting Models for Solar Power Generation (Week 2 AI/ML Deliverable)
Includes:
- LightGBM Gradient Boosted Decision Trees Forecaster (tabular weather + solar geometry + lags)
- Facebook Prophet Forecaster (additive time-series decomposition with exogenous weather regressors)
- Integrated Week 2 Evaluation Pipeline benchmarking Baselines vs LightGBM vs Prophet
"""

import logging
import warnings
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import lightgbm as lgb
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

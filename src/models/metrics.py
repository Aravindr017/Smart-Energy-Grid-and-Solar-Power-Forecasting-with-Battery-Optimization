"""
Evaluation Metrics for Solar Power Forecasting
Computes:
- Root Mean Squared Error (RMSE) - Overall & Daylight
- Mean Absolute Error (MAE) - Overall & Daylight
- Daylight Mean Absolute Percentage Error (Daylight MAPE)
- Normalized RMSE (nRMSE)
- Coefficient of Determination (R²)
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Union


def evaluate_forecast(
    y_true: Union[np.ndarray, pd.Series],
    y_pred: Union[np.ndarray, pd.Series],
    is_daylight: Optional[Union[np.ndarray, pd.Series]] = None,
    daylight_mape_min_actual: float = 10.0,
) -> Dict[str, float]:
    """
    Evaluates forecasting predictions against actual observations.
    
    Args:
        y_true: Actual solar generation values (kW).
        y_pred: Predicted solar generation values (kW).
        is_daylight: Boolean array/series indicating daylight intervals.
                     If None, defaults to y_true > 0.
        daylight_mape_min_actual: Minimum actual kW threshold to include in MAPE
                                  calculation to prevent division by near-zero.
                                  
    Returns:
        Dictionary of computed metric scores.
    """
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    
    # Clip negative predictions
    yp = np.maximum(0.0, yp)
    
    # 1. Overall Metrics
    diff = yt - yp
    mse_all = np.mean(diff ** 2)
    rmse_all = np.sqrt(mse_all)
    mae_all = np.mean(np.abs(diff))
    
    # Total sum of squares for R2
    ss_tot = np.sum((yt - np.mean(yt)) ** 2)
    ss_res = np.sum(diff ** 2)
    r2_all = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    # Normalized RMSE (relative to peak actual power)
    peak_power = np.max(yt) if len(yt) > 0 and np.max(yt) > 0 else 1.0
    nrmse_all = (rmse_all / peak_power) * 100.0

    # 2. Daylight Metrics
    if is_daylight is not None:
        day_mask = np.asarray(is_daylight, dtype=bool)
    else:
        day_mask = yt > 0.0

    yt_day = yt[day_mask]
    yp_day = yp[day_mask]

    if len(yt_day) > 0:
        diff_day = yt_day - yp_day
        rmse_day = float(np.sqrt(np.mean(diff_day ** 2)))
        mae_day = float(np.mean(np.abs(diff_day)))
        
        # Daylight MAPE on values >= daylight_mape_min_actual
        mape_mask = yt_day >= daylight_mape_min_actual
        if np.sum(mape_mask) > 0:
            mape_day = float(np.mean(np.abs(diff_day[mape_mask] / yt_day[mape_mask])) * 100.0)
        else:
            mape_day = float(np.nan)
            
        ss_tot_day = np.sum((yt_day - np.mean(yt_day)) ** 2)
        ss_res_day = np.sum(diff_day ** 2)
        r2_day = float(1.0 - (ss_res_day / ss_tot_day)) if ss_tot_day > 0 else 0.0
        nrmse_day = float((rmse_day / peak_power) * 100.0)
    else:
        rmse_day = float(np.nan)
        mae_day = float(np.nan)
        mape_day = float(np.nan)
        r2_day = float(np.nan)
        nrmse_day = float(np.nan)

    return {
        "rmse_overall": round(float(rmse_all), 2),
        "mae_overall": round(float(mae_all), 2),
        "r2_overall": round(float(r2_all), 4),
        "nrmse_overall_pct": round(float(nrmse_all), 2),
        "daylight_rmse": round(rmse_day, 2),
        "daylight_mae": round(mae_day, 2),
        "daylight_mape_pct": round(mape_day, 2) if not np.isnan(mape_day) else None,
        "daylight_r2": round(r2_day, 4),
        "daylight_nrmse_pct": round(nrmse_day, 2),
        "total_test_hours": int(len(yt)),
        "daylight_hours": int(len(yt_day)),
    }

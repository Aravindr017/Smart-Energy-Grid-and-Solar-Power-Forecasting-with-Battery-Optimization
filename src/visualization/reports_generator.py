"""
Reports & Visualizations Generator
Computes correlation matrices and exports publication-grade analytical plots to reports/figures/.
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Ensure project root is available in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.data.loader import load_processed_handoff
from src.features.engineering import create_feature_pipeline


def generate_correlation_reports(plant_id: int = 1, reports_dir: Path = None) -> pd.DataFrame:
    """
    Computes correlation matrix between target (AC Power) and physical/meteorological drivers.
    Saves CSV and high-resolution heatmap to reports/figures/.
    """
    if reports_dir is None:
        reports_dir = root_dir / "reports"
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    df_15min = load_processed_handoff(plant_id=plant_id, freq="15min")
    df_feat = create_feature_pipeline(df_15min, plant_id=plant_id, target_col="ac_power")

    analysis_cols = [
        "ac_power", "dc_power", "sensor_irradiation", "module_temperature",
        "sensor_temperature", "ghi", "direct_radiation", "dhi", "dni",
        "openmeteo_temperature", "humidity", "cloud", "wind_speed_10m",
        "cos_zenith", "solar_elevation_deg"
    ]
    avail_cols = [c for c in analysis_cols if c in df_feat.columns]
    corr = df_feat[avail_cols].corr()

    # Export correlation matrix CSV
    corr_csv = reports_dir / f"plant{plant_id}_correlations.csv"
    corr.to_csv(corr_csv)

    # Plot Correlation Heatmap
    plt.figure(figsize=(12, 10))
    sns.set_theme(style="white")
    mask = np.triu(np.ones_like(corr, dtype=bool))
    cmap = sns.diverging_palette(230, 20, as_cmap=True)

    sns.heatmap(
        corr,
        mask=mask,
        cmap=cmap,
        vmax=1.0,
        vmin=-1.0,
        center=0,
        square=True,
        linewidths=.5,
        cbar_kws={"shrink": .8, "label": "Pearson Correlation Coefficient"},
        annot=True,
        fmt=".2f",
        annot_kws={"size": 8}
    )
    plt.title(f"Plant {plant_id}: Correlation Matrix (Target & Meteorological Drivers)", fontsize=13, pad=16, weight="bold")
    plt.tight_layout()
    heatmap_path = figures_dir / f"plant{plant_id}_correlation_heatmap.png"
    plt.savefig(heatmap_path, dpi=300)
    plt.close()

    return corr


def generate_analytical_figures(plant_id: int = 1, reports_dir: Path = None):
    """
    Generates essential analytical figures:
    1. AC Power vs. Sensor Irradiation with Module Temperature Gradient
    2. 24-Hour Diurnal Generation Curve with Variance Band
    3. Out-of-sample Forecast: Actual vs. Predictions (7-day horizon)
    4. Prediction Error Residuals Distribution
    """
    if reports_dir is None:
        reports_dir = root_dir / "reports"
    figures_dir = reports_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    df_15min = load_processed_handoff(plant_id=plant_id, freq="15min")

    # 1. Weather Irradiance vs Power Scatter
    plt.figure(figsize=(9, 6))
    sns.set_theme(style="whitegrid")
    day_df = df_15min[df_15min["ac_power"] > 0].sample(n=min(5000, len(df_15min[df_15min["ac_power"] > 0])), random_state=42)
    
    scatter = plt.scatter(
        day_df["sensor_irradiation"],
        day_df["ac_power"],
        c=day_df["module_temperature"],
        cmap="coolwarm",
        alpha=0.6,
        edgecolors="none",
        s=15
    )
    cbar = plt.colorbar(scatter)
    cbar.set_label("Module Temperature (°C)", fontsize=10)
    plt.xlabel("Sensor Solar Irradiation (W/m² or kW/m²)", fontsize=11)
    plt.ylabel("Inverter AC Power Output (kW)", fontsize=11)
    plt.title(f"Plant {plant_id}: AC Power vs. Solar Irradiation (Module Temp Effect)", fontsize=12, weight="bold")
    plt.tight_layout()
    plt.savefig(figures_dir / f"plant{plant_id}_weather_irradiance_scatter.png", dpi=300)
    plt.close()

    # 2. 24-Hour Diurnal Generation Profile
    plt.figure(figsize=(9, 5))
    df_diurnal = df_15min.copy()
    df_diurnal["time"] = pd.to_datetime(df_diurnal["time"])
    df_diurnal["hour"] = df_diurnal["time"].dt.hour
    hourly_stats = df_diurnal.groupby("hour")["ac_power"].agg(["mean", "std", "min", "max"]).reset_index()

    plt.plot(hourly_stats["hour"], hourly_stats["mean"], color="#0f172a", lw=2.5, marker="o", label="Mean Output")
    plt.fill_between(
        hourly_stats["hour"],
        np.maximum(0, hourly_stats["mean"] - hourly_stats["std"]),
        hourly_stats["mean"] + hourly_stats["std"],
        color="#38bdf8",
        alpha=0.3,
        label="±1 Std Dev"
    )
    plt.xlabel("Hour of Day (0–23)", fontsize=11)
    plt.ylabel("AC Power Output (kW)", fontsize=11)
    plt.title(f"Plant {plant_id}: Mean 24-Hour Diurnal Generation Profile", fontsize=12, weight="bold")
    plt.xticks(range(0, 24))
    plt.legend(frameon=True)
    plt.tight_layout()
    plt.savefig(figures_dir / f"plant{plant_id}_diurnal_generation_profile.png", dpi=300)
    plt.close()

    # 3. Out-of-sample Forecast Comparison Plot
    pred_file = reports_dir / f"plant{plant_id}_week1_baseline_predictions.csv"
    if pred_file.exists():
        df_preds = pd.read_csv(pred_file)
        df_preds["time"] = pd.to_datetime(df_preds["time"])
        
        # Aggregate to plant-level total for clear visualization
        num_cols = [c for c in df_preds.columns if c not in ["time", "source_key"]]
        df_plot = df_preds.groupby("time")[num_cols].sum().reset_index().sort_values("time")

        plt.figure(figsize=(14, 5))
        plt.plot(df_plot["time"], df_plot["actual_ac_power"], label="Actual Total Power", color="#0f172a", lw=2)
        
        if "pred_ridge_regression" in df_plot.columns:
            plt.plot(df_plot["time"], df_plot["pred_ridge_regression"], label="Ridge Baseline", color="#2563eb", lw=1.75, ls="--")
        if "pred_persistence_24h_lag" in df_plot.columns:
            plt.plot(df_plot["time"], df_plot["pred_persistence_24h_lag"], label="Persistence (24h)", color="#f59e0b", lw=1.2, ls=":")

        plt.xlabel("Date & Time", fontsize=11)
        plt.ylabel("Plant Total AC Output (kW)", fontsize=11)
        plt.title(f"Plant {plant_id}: Out-of-Sample 7-Day Horizon (Actual vs. Baselines)", fontsize=12, weight="bold")
        plt.legend(frameon=True, loc="upper right")
        plt.tight_layout()
        plt.savefig(figures_dir / f"plant{plant_id}_actual_vs_predicted_7days.png", dpi=300)
        plt.close()

        # 4. Residuals Error Distribution
        if "pred_ridge_regression" in df_plot.columns:
            residuals = df_plot["actual_ac_power"] - df_plot["pred_ridge_regression"]
            plt.figure(figsize=(8, 4.5))
            sns.histplot(residuals, kde=True, color="#2563eb", bins=40)
            plt.axvline(0, color="red", linestyle="--", lw=1.5)
            plt.xlabel("Forecast Error / Residual (kW)", fontsize=11)
            plt.ylabel("Frequency", fontsize=11)
            plt.title(f"Plant {plant_id}: Ridge Regression Residuals Distribution", fontsize=12, weight="bold")
            plt.tight_layout()
            plt.savefig(figures_dir / f"plant{plant_id}_residuals_distribution.png", dpi=300)
            plt.close()


def generate_all_reports():
    """Generates all reports and figures for Plant 1 and Plant 2."""
    reports_dir = root_dir / "reports"
    for pid in [1, 2]:
        print(f"Generating correlations and figures for Plant {pid}...")
        generate_correlation_reports(plant_id=pid, reports_dir=reports_dir)
        generate_analytical_figures(plant_id=pid, reports_dir=reports_dir)
    print("All figures saved to reports/figures/ successfully.")


if __name__ == "__main__":
    generate_all_reports()

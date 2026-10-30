"""
Week 2 AI/ML Benchmark & Battery Optimization Runner
Executes:
1. Advanced Solar Forecasting Benchmark (Persistence vs Ridge vs Prophet vs LightGBM)
2. Exports evaluation metrics and test horizon predictions to reports/
3. Solves the 24-hour Battery Optimization (PuLP LP) on forecasted solar profiles
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure project root is available in sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.data.loader import load_processed_handoff
from src.models.forecasting import run_week2_forecasting_benchmark
from src.optimization.battery_lp import BatterySpecs, TOUTariff, BatteryOptimizerLP


def main():
    print("=" * 85)
    print("⚡ WEEK 2 AI/ML: ADVANCED FORECASTING & PuLP BATTERY OPTIMIZATION")
    print("=" * 85)

    reports_dir = root_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    all_metrics = []

    for plant_id in [1, 2]:
        print(f"\n--- [1/2] Benchmarking Plant {plant_id} Advanced Forecasters (7-Day Test Horizon) ---")
        # Load 15-minute handoff dataset
        df_15min = load_processed_handoff(plant_id=plant_id, freq="15min")
        print(f"Loaded {len(df_15min):,} records across {df_15min['source_key'].nunique()} inverters.")

        metrics_df, test_df, preds_dict, feat_imp = run_week2_forecasting_benchmark(
            df_15min,
            plant_id=plant_id,
            test_days=7,
        )

        print(f"\nPlant {plant_id} Forecast Leaderboard (Sorted by Daylight RMSE):")
        print(metrics_df.to_string(index=False))

        # Save predictions to reports/
        pred_dict_export = {"time": test_df["time"], "actual_ac_power": test_df["ac_power"]}
        if "source_key" in test_df.columns:
            pred_dict_export["source_key"] = test_df["source_key"]

        for m_name, preds in preds_dict.items():
            clean_name = f"pred_{m_name.lower().split()[0]}"
            pred_dict_export[clean_name] = preds

        pred_df = pd.DataFrame(pred_dict_export)
        pred_csv = reports_dir / f"plant{plant_id}_week2_forecasting_predictions.csv"
        pred_df.to_csv(pred_csv, index=False)
        print(f"✔ Saved {len(pred_df):,} test predictions to: {pred_csv.name}")

        # Save feature importances
        feat_csv = reports_dir / f"plant{plant_id}_lightgbm_feature_importance.csv"
        feat_imp.to_csv(feat_csv, index=False)
        print(f"✔ Saved LightGBM feature importance rankings to: {feat_csv.name}")

        metrics_df["plant_id"] = plant_id
        all_metrics.append(metrics_df)

    # Save combined metrics summary
    combined_metrics = pd.concat(all_metrics, ignore_index=True)
    combined_csv = reports_dir / "week2_forecasting_metrics_summary.csv"
    combined_metrics.to_csv(combined_csv, index=False)
    print(f"\n✔ Saved complete Week 2 forecasting leaderboard to: {combined_csv.name}")

    # -------------------------------------------------------------
    # 2. PuLP Linear Programming Battery Optimization Demo
    # -------------------------------------------------------------
    print("\n" + "=" * 85)
    print("🔋 [2/2] SOLVING 24-HOUR PuLP BATTERY ARBITRAGE OPTIMIZATION (PLANT 1)")
    print("=" * 85)

    # Use hourly aggregated data for 24-hour day-ahead market dispatch
    df_hourly = load_processed_handoff(plant_id=1, freq="hourly")
    # Take the last 24 hours of the dataset as the optimization day
    day24 = df_hourly.tail(24).copy().reset_index(drop=True)
    
    # Configure battery sized appropriately for a 25 MW solar plant:
    # 10 MWh storage capacity (10,000 kWh), 5 MW inverter (5,000 kW)
    specs = BatterySpecs(
        capacity_kwh=10000.0,
        max_charge_kw=5000.0,
        max_discharge_kw=5000.0,
        charge_efficiency=0.95,
        discharge_efficiency=0.95,
        soc_min=0.10,
        soc_max=0.90,
        soc_initial=0.20,
        degradation_cost_per_kwh=0.005,
    )
    tariff = TOUTariff(
        off_peak_rate=0.05,
        normal_rate=0.10,
        peak_rate=0.25,
        export_feedin_rate=0.04,
    )

    optimizer = BatteryOptimizerLP(specs=specs, tariff=tariff)
    results = optimizer.optimize_dispatch(
        solar_kw=day24["ac_power"].values,
        timestamps=day24["time"],
        dt_hours=1.0,
        enforce_terminal_soc=True,
    )

    kpis = results["kpi_summary"]
    schedule_df = results["schedule_df"]

    print(f"Solver Status: {kpis['solver_status']}")
    print(f"Electricity Cost Without BESS : ${kpis['cost_without_bess']:,.2f}")
    print(f"Electricity Cost With BESS    : ${kpis['cost_with_bess']:,.2f}")
    print(f"Net Arbitrage Savings         : ${kpis['net_arbitrage_savings']:,.2f} ({kpis['savings_percentage']:.1f}% reduction)")
    print(f"Peak Grid Import Shaved       : {kpis['peak_demand_shaved_kw']:,.1f} kW ({kpis['peak_shaving_percentage']:.1f}% shaved)")
    print(f"Solar Self-Consumption        : {kpis['solar_self_consumption_without_bess_pct']:.1f}% -> {kpis['solar_self_consumption_with_bess_pct']:.1f}%")
    print(f"Equivalent Full Cycles Used   : {kpis['equivalent_full_cycles']} cycles")

    dispatch_csv = reports_dir / "sample_battery_dispatch_plant1.csv"
    schedule_df.to_csv(dispatch_csv, index=False)
    print(f"✔ Saved 24-hour battery schedule to: {dispatch_csv.name}")
    print("\nWeek 2 AI/ML Execution Completed Successfully!")


if __name__ == "__main__":
    main()

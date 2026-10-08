"""
Week 1 AI/ML Benchmark Runner
Trains and evaluates all baseline models on Plant 1 and Plant 2 hourly data,
prints formatted benchmark tables, and exports results to reports/.
"""

import sys
import json
from pathlib import Path
import pandas as pd

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.data.loader import load_processed_handoff
from src.models.baseline import run_week1_baseline_benchmark


def main():
    print("=" * 80)
    print("⚡ WEEK 1 AI/ML BENCHMARK: SOLAR GENERATION FORECASTING BASELINES")
    print("=" * 80)

    reports_dir = root_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    all_metrics = []

    for plant_id in [1, 2]:
        print(f"\n--- Benchmarking Plant {plant_id} (15-Minute Resolution, Inverter-Level 68k Dataset) ---")
        df_15min = load_processed_handoff(plant_id=plant_id, freq="15min")
        print(f"Loaded {len(df_15min):,} observations across {df_15min['source_key'].nunique()} inverters.")
        
        metrics_df, test_df, preds_dict = run_week1_baseline_benchmark(
            df_15min,
            plant_id=plant_id,
            test_days=7,
        )
        
        print(f"\nPlant {plant_id} Baseline Results (Sorted by Daylight RMSE):")
        print(metrics_df.to_string(index=False))

        # Save predictions for test horizon
        pred_dict_export = {"time": test_df["time"], "actual_ac_power": test_df["ac_power"]}
        if "source_key" in test_df.columns:
            pred_dict_export["source_key"] = test_df["source_key"]

        for m_name, preds in preds_dict.items():
            col_name = f"pred_{m_name.lower().replace(' ', '_').replace('(', '').replace(')', '')}"
            pred_dict_export[col_name] = preds

        pred_export = pd.DataFrame(pred_dict_export)
        pred_csv = reports_dir / f"plant{plant_id}_week1_baseline_predictions.csv"
        pred_export.to_csv(pred_csv, index=False)
        print(f"Saved {len(pred_export):,} test predictions to: {pred_csv}")

        metrics_df["plant_id"] = plant_id
        all_metrics.append(metrics_df)

    combined_metrics = pd.concat(all_metrics, ignore_index=True)
    combined_csv = reports_dir / "week1_baseline_metrics_summary.csv"
    combined_metrics.to_csv(combined_csv, index=False)
    print(f"\n✔ Saved combined metrics summary to: {combined_csv}")
    print("\nWeek 1 AI/ML Baseline Execution Completed Successfully!")


if __name__ == "__main__":
    main()

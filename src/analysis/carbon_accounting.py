"""
Carbon Accounting & Avoided Emissions Module (Week 4 Deliverable)
Estimates operational CO2 emission offsets enabled by solar PV generation
and PuLP battery storage load-shifting.

Methodology:
    Avoided Emissions (kg CO2e) = Displaced Grid Electricity (kWh) * Grid Emission Factor (kg CO2e/kWh)
    Avoided Emissions (tonnes CO2e) = Avoided Emissions (kg CO2e) / 1000.0

Grid Emission Factor Provenance:
    - Organization: Central Electricity Authority (CEA), Ministry of Power, Government of India
    - Reference Publication: "CO2 Baseline Database for the Indian Power Sector", User Guide Version 19.0 (2023-2024)
    - Default Value: 0.716 kg CO2e/kWh (National Weighted Average Grid Emission Rate including renewables)
    - Operating Margin Value: 0.820 kg CO2e/kWh (Thermal marginal baseline)
    - System Boundary: Operational displacement of utility grid generation.
      Excludes cradle-to-grave lifecycle embodied emissions (LCA) of PV modules and BESS cells.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

# Ensure project root is available in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Headless matplotlib configuration
os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.data.loader import load_processed_handoff
from src.optimization.battery_lp import BatterySpecs, TOUTariff, BatteryOptimizerLP
from src.analysis.weather_stress_test import SCENARIOS, apply_weather_stress_scenario

# Official Provenance Metadata
GRID_EMISSION_PROVENANCE = {
    "source_organization": "Central Electricity Authority (CEA), Ministry of Power, Government of India",
    "source_document": "CO2 Baseline Database for the Indian Power Sector, User Guide Version 19.0",
    "publication_year": "2023-2024",
    "geographic_scope": "National Grid (Unified Indian Synchronous Grid, Southern Region / AP)",
    "default_emission_factor_kg_per_kwh": 0.716,
    "marginal_emission_factor_kg_per_kwh": 0.820,
    "unit": "kg CO2e / kWh",
    "is_provisional": False,
    "boundary_note": "Operational displacement at transmission interface; excludes module/battery lifecycle manufacturing LCA emissions."
}

DEFAULT_EMISSION_FACTORS = [0.50, 0.716, 0.820, 0.95]


def calculate_carbon_offsets(
    grid_import_without_bess_kwh: float,
    grid_import_with_bess_kwh: float,
    solar_generation_kwh: float,
    solar_exported_kwh: float,
    grid_emission_factor: float = 0.716,
) -> Dict[str, Any]:
    """
    Computes rigorous carbon accounting metrics based on power flows and grid emission factor.
    """
    # 1. Grid electricity displaced strictly by battery arbitrage (peak shaving & load shifting)
    displaced_grid_by_bess_kwh = max(0.0, grid_import_without_bess_kwh - grid_import_with_bess_kwh)
    storage_avoided_co2_kg = displaced_grid_by_bess_kwh * grid_emission_factor

    # 2. Solar electricity directly self-consumed (displacing immediate grid purchase)
    solar_self_consumed_kwh = max(0.0, solar_generation_kwh - solar_exported_kwh)
    solar_self_consumed_avoided_co2_kg = solar_self_consumed_kwh * grid_emission_factor

    # 3. Total operational grid emissions under baseline vs BESS
    baseline_grid_emissions_kg = grid_import_without_bess_kwh * grid_emission_factor
    optimized_grid_emissions_kg = grid_import_with_bess_kwh * grid_emission_factor

    # 4. Total combined avoided operational emissions (Solar + BESS shifting)
    total_avoided_co2_kg = storage_avoided_co2_kg + solar_self_consumed_avoided_co2_kg

    return {
        "grid_emission_factor_kg_per_kwh": grid_emission_factor,
        "grid_import_without_bess_kwh": round(grid_import_without_bess_kwh, 2),
        "grid_import_with_bess_kwh": round(grid_import_with_bess_kwh, 2),
        "displaced_grid_electricity_kwh": round(displaced_grid_by_bess_kwh, 2),
        "baseline_grid_emissions_kg": round(baseline_grid_emissions_kg, 2),
        "optimized_grid_emissions_kg": round(optimized_grid_emissions_kg, 2),
        "storage_avoided_co2_kg": round(storage_avoided_co2_kg, 2),
        "storage_avoided_co2_tonnes": round(storage_avoided_co2_kg / 1000.0, 4),
        "solar_self_consumed_avoided_co2_kg": round(solar_self_consumed_avoided_co2_kg, 2),
        "solar_self_consumed_avoided_co2_tonnes": round(solar_self_consumed_avoided_co2_kg / 1000.0, 4),
        "total_avoided_co2_kg": round(total_avoided_co2_kg, 2),
        "total_avoided_co2_tonnes": round(total_avoided_co2_kg / 1000.0, 4),
        "emissions_reduction_pct": round((storage_avoided_co2_kg / baseline_grid_emissions_kg * 100.0), 2) if baseline_grid_emissions_kg > 0 else 0.0,
        "annual_projected_avoided_co2_tonnes": round((total_avoided_co2_kg * 365.0) / 1000.0, 2),
    }


def run_carbon_scenario_analysis(
    plant_id: int = 1,
    emission_factors: Optional[List[float]] = None,
    save_artifacts: bool = True,
) -> Dict[str, Any]:
    """
    Evaluates carbon offset dynamics across:
    1. Grid emission factor sensitivity (0.50 to 0.95 kg CO2e/kWh)
    2. Operational weather stress scenarios
    """
    if emission_factors is None:
        emission_factors = [0.50, 0.716, 0.820, 0.95]

    df_hourly = load_processed_handoff(plant_id=plant_id, freq="hourly")
    day_slice = df_hourly.tail(24).copy().reset_index(drop=True)

    specs = BatterySpecs(
        capacity_kwh=10000.0,
        max_charge_kw=5000.0,
        max_discharge_kw=5000.0,
        soc_initial=0.20,
        soc_min=0.10,
        soc_max=0.90,
    )
    tariff = TOUTariff()
    optimizer = BatteryOptimizerLP(specs=specs, tariff=tariff)

    # 1. Base Day Optimization
    base_res = optimizer.optimize_dispatch(
        solar_kw=day_slice["ac_power"].values,
        timestamps=pd.to_datetime(day_slice["time"]),
        dt_hours=1.0,
    )
    base_sched = base_res["schedule_df"]
    base_imp_unman = float(np.sum(base_sched["grid_import_unmanaged_kw"]))
    base_imp_bess = float(np.sum(base_sched["grid_import_with_bess_kw"]))
    base_solar = float(np.sum(base_sched["solar_generation_kw"]))
    base_export = float(np.sum(base_sched["grid_export_with_bess_kw"]))

    # Emission factor sensitivity table
    ef_records = []
    for ef in emission_factors:
        c_res = calculate_carbon_offsets(
            grid_import_without_bess_kwh=base_imp_unman,
            grid_import_with_bess_kwh=base_imp_bess,
            solar_generation_kwh=base_solar,
            solar_exported_kwh=base_export,
            grid_emission_factor=ef,
        )
        c_res["scenario"] = "Normal (Clear Sky)"
        c_res["factor_label"] = (
            "Clean / Low-Carbon Grid (0.50)" if ef == 0.50
            else ("Official CEA Baseline 2024 (0.716)" if ef == 0.716
            else ("CEA Thermal Marginal (0.820)" if ef == 0.820
            else "High-Coal Subcritical Grid (0.95)"))
        )
        ef_records.append(c_res)

    df_ef_sensitivity = pd.DataFrame(ef_records)

    # 2. Weather stress carbon scenarios (using default CEA factor 0.716)
    weather_records = []
    for sc_name, sc_info in SCENARIOS.items():
        stressed_day = apply_weather_stress_scenario(day_slice, scenario_name=sc_name)
        opt_st = optimizer.optimize_dispatch(
            solar_kw=stressed_day["ac_power_stressed"].values,
            timestamps=pd.to_datetime(stressed_day["time"]),
            dt_hours=1.0,
        )
        sched_st = opt_st["schedule_df"]
        st_imp_unman = float(np.sum(sched_st["grid_import_unmanaged_kw"]))
        st_imp_bess = float(np.sum(sched_st["grid_import_with_bess_kw"]))
        st_solar = float(np.sum(sched_st["solar_generation_kw"]))
        st_export = float(np.sum(sched_st["grid_export_with_bess_kw"]))

        c_st = calculate_carbon_offsets(
            grid_import_without_bess_kwh=st_imp_unman,
            grid_import_with_bess_kwh=st_imp_bess,
            solar_generation_kwh=st_solar,
            solar_exported_kwh=st_export,
            grid_emission_factor=0.716,
        )
        c_st["total_solar_generation_mwh"] = round(st_solar / 1000.0, 2)
        c_st["scenario_name"] = sc_name
        c_st["scenario_label"] = sc_info["label"]
        c_st["is_synthetic"] = sc_info["is_synthetic"]
        weather_records.append(c_st)

    df_weather_carbon = pd.DataFrame(weather_records)

    if save_artifacts:
        reports_dir = ROOT_DIR / "reports"
        figures_dir = reports_dir / "figures"
        reports_dir.mkdir(parents=True, exist_ok=True)
        figures_dir.mkdir(parents=True, exist_ok=True)

        df_ef_sensitivity.to_csv(reports_dir / "week4_carbon_summary.csv", index=False)
        df_weather_carbon.to_csv(reports_dir / "week4_carbon_scenarios.csv", index=False)

        # Plot Carbon Offset Comparison
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=300)

        # Subplot 1: Sensitivity across grid emission factors
        ax1.bar(
            df_ef_sensitivity["factor_label"],
            df_ef_sensitivity["storage_avoided_co2_tonnes"],
            color=["#38bdf8", "#0284c7", "#0369a1", "#075985"],
            edgecolor="#0f172a",
            width=0.55
        )
        ax1.set_ylabel("Storage Avoided CO2 (Tonnes / Day)", fontsize=10, fontweight="bold")
        ax1.set_title("BESS Daily Avoided CO2 Across Grid Emission Factors", fontsize=11, fontweight="bold")
        ax1.set_xticks(range(len(df_ef_sensitivity)))
        ax1.set_xticklabels(df_ef_sensitivity["factor_label"], rotation=25, ha="right", fontsize=8.5)
        ax1.grid(axis="y", linestyle="--", alpha=0.5)

        # Subplot 2: Weather stress scenario avoided CO2
        ax2.bar(
            df_weather_carbon["scenario_label"],
            df_weather_carbon["total_avoided_co2_tonnes"],
            color="#10b981",
            edgecolor="#064e3b",
            width=0.55
        )
        ax2.set_ylabel("Total Avoided CO2 (Tonnes / Day)", fontsize=10, fontweight="bold")
        ax2.set_title("Total Avoided CO2 (Solar + BESS) Under Weather Stress (CEA 0.716)", fontsize=11, fontweight="bold")
        ax2.set_xticks(range(len(df_weather_carbon)))
        ax2.set_xticklabels(df_weather_carbon["scenario_label"], rotation=25, ha="right", fontsize=8.5)
        ax2.grid(axis="y", linestyle="--", alpha=0.5)

        plt.tight_layout()
        plt.savefig(figures_dir / "week4_carbon_comparison.png")
        plt.close(fig)

    return {
        "plant_id": plant_id,
        "provenance": GRID_EMISSION_PROVENANCE,
        "sensitivity_df": df_ef_sensitivity,
        "weather_scenarios_df": df_weather_carbon,
    }


if __name__ == "__main__":
    print("Executing Week 4 Carbon Accounting Suite...")
    res = run_carbon_scenario_analysis(plant_id=1, save_artifacts=True)
    print("[OK] Carbon accounting suite executed successfully.")
    print("Default CEA Baseline (0.716 kg/kWh) Summary:")
    print(res["sensitivity_df"][["factor_label", "storage_avoided_co2_tonnes", "total_avoided_co2_tonnes", "annual_projected_avoided_co2_tonnes"]])

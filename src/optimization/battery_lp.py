"""
Battery Energy Storage System (BESS) Linear Programming Optimization (Week 2 AI/ML Deliverable)
Formulated with PuLP for:
- Time-of-Use (TOU) Energy Arbitrage
- Solar Self-Consumption Maximization
- Peak Shaving & Duck Curve Mitigation
- Operational Constraints: State-of-Charge (SoC), C-rate, Round-trip Efficiency & Degradation
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import pulp


@dataclass
class BatterySpecs:
    """
    Physical & operational specifications of a Battery Energy Storage System (BESS).
    
    Attributes:
        capacity_kwh: Total nominal storage capacity in kWh (e.g. 5,000 kWh = 5 MWh).
        max_charge_kw: Maximum continuous charging power in kW.
        max_discharge_kw: Maximum continuous discharging power in kW.
        charge_efficiency: One-way charging efficiency (e.g. 0.95 = 95%).
        discharge_efficiency: One-way discharging efficiency (e.g. 0.95 = 95%).
        soc_min: Minimum allowable State-of-Charge as fraction of capacity (e.g. 0.10).
        soc_max: Maximum allowable State-of-Charge as fraction of capacity (e.g. 0.90).
        soc_initial: Initial State-of-Charge at start of horizon (e.g. 0.20).
        degradation_cost_per_kwh: Amortized battery throughput degradation wear cost ($/kWh).
    """
    capacity_kwh: float = 5000.0
    max_charge_kw: float = 2500.0
    max_discharge_kw: float = 2500.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    soc_min: float = 0.10
    soc_max: float = 0.90
    soc_initial: float = 0.20
    degradation_cost_per_kwh: float = 0.005

    @property
    def round_trip_efficiency(self) -> float:
        """Total round-trip AC-to-AC battery efficiency."""
        return self.charge_efficiency * self.discharge_efficiency


@dataclass
class TOUTariff:
    """
    Time-of-Use (TOU) Electricity Pricing Matrix.
    
    Standard 3-tier industrial tariff structure:
    - Off-Peak (overnight / solar morning): Low cost
    - Normal / Shoulder (daytime): Moderate cost
    - Peak (evening 17:00-21:00): Highest cost (Duck curve peak demand)
    """
    off_peak_rate: float = 0.05    # $/kWh (or ₹/kWh)
    normal_rate: float = 0.10      # $/kWh
    peak_rate: float = 0.25        # $/kWh
    export_feedin_rate: float = 0.04  # $/kWh (solar export back to grid)
    
    peak_hours: Tuple[int, ...] = (17, 18, 19, 20)
    normal_hours: Tuple[int, ...] = (6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 21)
    off_peak_hours: Tuple[int, ...] = (22, 23, 0, 1, 2, 3, 4, 5)

    def get_rates_for_series(self, timestamps: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generates import and export price vectors matching the provided timestamp series.
        """
        dt_idx = pd.DatetimeIndex(timestamps)
        hours = dt_idx.hour.values
        import_rates = np.full(len(hours), self.normal_rate, dtype=float)
        
        # Off-peak hours
        off_mask = np.isin(hours, self.off_peak_hours)
        import_rates[off_mask] = self.off_peak_rate
        
        # Peak hours
        peak_mask = np.isin(hours, self.peak_hours)
        import_rates[peak_mask] = self.peak_rate
        
        export_rates = np.full(len(hours), self.export_feedin_rate, dtype=float)
        return import_rates, export_rates


def create_synthetic_load_profile(
    solar_kw: Union[np.ndarray, pd.Series],
    timestamps: Optional[Union[np.ndarray, pd.Series]] = None,
) -> np.ndarray:
    """Create the modeled facility demand profile used when no measured load is available."""
    solar = np.asarray(solar_kw, dtype=float)
    if timestamps is not None:
        time_index = pd.DatetimeIndex(timestamps)
        if len(time_index) != len(solar):
            raise ValueError("timestamps and solar_kw must have the same length.")
        hours = time_index.hour + time_index.minute / 60.0
    else:
        hours = np.arange(len(solar)) % 24

    mean_solar = max(100.0, np.mean(solar[solar > 0])) if np.any(solar > 0) else 1000.0
    base_curve = 0.5 + 0.2 * np.sin((hours - 8) * np.pi / 12) + 0.4 * np.exp(-((hours - 19) ** 2) / 8.0)
    return base_curve * mean_solar * 0.85


class BatteryOptimizerLP:
    """
    Linear Programming (LP) Battery Arbitrage & Dispatch Optimizer.
    
    Formulated mathematically in PuLP:
    
    Decision Variables (for each time step t = 1 ... T):
        P_ch[t]    : Battery charging power from solar / grid (kW) >= 0
        P_dis[t]   : Battery discharging power to load / grid (kW) >= 0
        E[t]       : Energy stored in battery at step t (kWh)
        P_imp[t]   : Power imported from external grid (kW) >= 0
        P_exp[t]   : Power exported to external grid (kW) >= 0
        
    Objective:
        Minimize Net Grid Cost over horizon T:
            min sum_t ( C_imp[t] * P_imp[t] * dt 
                      - C_exp[t] * P_exp[t] * dt 
                      + C_deg * (P_ch[t] + P_dis[t]) * dt )
                      
    Constraints (for all t):
        1. Power Balance:
           P_solar[t] + P_dis[t] + P_imp[t] == P_load[t] + P_ch[t] + P_exp[t]
           
        2. State of Charge (SoC) Dynamics:
           E[t] == E[t-1] + ( eta_ch * P_ch[t] - (1 / eta_dis) * P_dis[t] ) * dt
           with E[0] == soc_initial * capacity_kwh
           
        3. Energy Limits:
           soc_min * capacity_kwh <= E[t] <= soc_max * capacity_kwh
           
        4. Power Limits:
           0 <= P_ch[t] <= max_charge_kw
           0 <= P_dis[t] <= max_discharge_kw
           
        5. Terminal State Condition:
           E[T] >= E[0] (Prevents model from exhausting battery at horizon end)
    """
    def __init__(
        self,
        specs: Optional[BatterySpecs] = None,
        tariff: Optional[TOUTariff] = None,
    ):
        self.specs = specs if specs is not None else BatterySpecs()
        self.tariff = tariff if tariff is not None else TOUTariff()

    def optimize_dispatch(
        self,
        solar_kw: Union[np.ndarray, pd.Series],
        load_kw: Optional[Union[np.ndarray, pd.Series]] = None,
        timestamps: Optional[pd.Series] = None,
        dt_hours: float = 1.0,
        enforce_terminal_soc: bool = True,
    ) -> Dict[str, Union[pd.DataFrame, Dict[str, float], str]]:
        """
        Solves the LP battery dispatch schedule.
        
        Args:
            solar_kw: Forecasted or actual solar generation in kW (length T).
            load_kw: Baseline grid load demand in kW (length T). If None, generates
                     a synthetic evening-peaking industrial load curve.
            timestamps: Optional timestamp Series corresponding to the horizon steps.
            dt_hours: Duration of each step in hours (1.0 for hourly, 0.25 for 15-min).
            enforce_terminal_soc: If True, requires final SoC >= initial SoC.
            
        Returns:
            Dictionary containing:
                'schedule_df': Full time-step dispatch schedule and SoC evolution.
                'kpi_summary': Economic and technical performance metrics.
                'solver_status': Status of the LP solver ('Optimal', etc.).
        """
        P_sol = np.asarray(solar_kw, dtype=float)
        T = len(P_sol)
        
        if load_kw is None:
            P_load = create_synthetic_load_profile(P_sol, timestamps)
        else:
            P_load = np.asarray(load_kw, dtype=float)

        if timestamps is not None:
            c_import, c_export = self.tariff.get_rates_for_series(timestamps)
        else:
            # Assume 24-hour repeating tariff
            dummy_dates = pd.date_range("2020-01-01", periods=T, freq=f"{int(dt_hours*60)}min")
            c_import, c_export = self.tariff.get_rates_for_series(dummy_dates)

        # -------------------------------------------------------------
        # PuLP Problem Formulation
        # -------------------------------------------------------------
        prob = pulp.LpProblem("Battery_Arbitrage_Optimization", pulp.LpMinimize)

        # Decision Variables
        P_ch = [pulp.LpVariable(f"P_ch_{t}", lowBound=0.0, upBound=self.specs.max_charge_kw) for t in range(T)]
        P_dis = [pulp.LpVariable(f"P_dis_{t}", lowBound=0.0, upBound=self.specs.max_discharge_kw) for t in range(T)]
        P_imp = [pulp.LpVariable(f"P_imp_{t}", lowBound=0.0) for t in range(T)]
        P_exp = [pulp.LpVariable(f"P_exp_{t}", lowBound=0.0) for t in range(T)]
        
        E_min = self.specs.soc_min * self.specs.capacity_kwh
        E_max = self.specs.soc_max * self.specs.capacity_kwh
        E_init = self.specs.soc_initial * self.specs.capacity_kwh
        
        E = [pulp.LpVariable(f"E_{t}", lowBound=E_min, upBound=E_max) for t in range(T)]

        # Objective Function: Minimize Net Grid Import Cost - Export Revenue + Degradation Cost
        objective = pulp.lpSum([
            (c_import[t] * P_imp[t] * dt_hours)
            - (c_export[t] * P_exp[t] * dt_hours)
            + (self.specs.degradation_cost_per_kwh * (P_ch[t] + P_dis[t]) * dt_hours)
            for t in range(T)
        ])
        prob += objective, "Total_Net_Cost"

        # Constraints
        eta_ch = self.specs.charge_efficiency
        eta_dis = self.specs.discharge_efficiency

        for t in range(T):
            # 1. Instantaneous Power Balance
            prob += (
                P_sol[t] + P_dis[t] + P_imp[t] == P_load[t] + P_ch[t] + P_exp[t],
                f"Power_Balance_{t}"
            )

            # 2. Battery SoC Dynamics
            prev_energy = E_init if t == 0 else E[t - 1]
            prob += (
                E[t] == prev_energy + (eta_ch * P_ch[t] - (1.0 / eta_dis) * P_dis[t]) * dt_hours,
                f"SoC_Dynamics_{t}"
            )

        # 3. Terminal SoC Constraint (prevents full depletion free-riding)
        if enforce_terminal_soc:
            prob += (E[T - 1] >= E_init, "Terminal_SoC_Condition")

        # Solve LP using standard CBC solver
        solver = pulp.PULP_CBC_CMD(msg=0)
        status = prob.solve(solver)
        solver_status_str = pulp.LpStatus[status]

        if status != pulp.constants.LpStatusOptimal:
            # Handle non-optimal / infeasible solver states gracefully without fabricating schedules
            return {
                "schedule_df": pd.DataFrame(),
                "kpi_summary": {
                    "solver_status": solver_status_str,
                    "error": f"Solver failed to find an optimal solution (status: {solver_status_str})",
                    "cost_without_bess": 0.0,
                    "cost_with_bess": 0.0,
                    "degradation_wear_cost": 0.0,
                    "gross_arbitrage_savings": 0.0,
                    "net_arbitrage_savings": 0.0,
                    "savings_percentage": 0.0,
                    "peak_grid_import_without_bess_kw": 0.0,
                    "peak_grid_import_with_bess_kw": 0.0,
                    "peak_demand_shaved_kw": 0.0,
                    "peak_shaving_percentage": 0.0,
                    "solar_self_consumption_without_bess_pct": 0.0,
                    "solar_self_consumption_with_bess_pct": 0.0,
                    "battery_total_throughput_kwh": 0.0,
                    "equivalent_full_cycles": 0.0,
                },
                "solver_status": solver_status_str,
            }

        # -------------------------------------------------------------
        # Extract Results
        # -------------------------------------------------------------
        ch_vals = np.array([float(pulp.value(P_ch[t]) or 0.0) for t in range(T)])
        dis_vals = np.array([float(pulp.value(P_dis[t]) or 0.0) for t in range(T)])
        imp_vals = np.array([float(pulp.value(P_imp[t]) or 0.0) for t in range(T)])
        exp_vals = np.array([float(pulp.value(P_exp[t]) or 0.0) for t in range(T)])
        e_vals = np.array([float(pulp.value(E[t]) or 0.0) for t in range(T)])

        # Strictly enforce mutual exclusivity of simultaneous charging and discharging
        simultaneous_mask = (ch_vals > 1e-4) & (dis_vals > 1e-4)
        if np.any(simultaneous_mask):
            for t in np.where(simultaneous_mask)[0]:
                net_p = ch_vals[t] - dis_vals[t]
                if net_p >= 0:
                    ch_vals[t] = net_p
                    dis_vals[t] = 0.0
                else:
                    ch_vals[t] = 0.0
                    dis_vals[t] = -net_p

        soc_pct = (e_vals / self.specs.capacity_kwh) * 100.0

        # Net load seen by the grid:
        # Without Battery: Load - Solar
        unmanaged_net_grid = P_load - P_sol
        unmanaged_imp = np.maximum(0.0, unmanaged_net_grid)
        unmanaged_exp = np.maximum(0.0, -unmanaged_net_grid)
        unmanaged_cost = np.sum((c_import * unmanaged_imp - c_export * unmanaged_exp) * dt_hours)

        # With Battery:
        optimized_grid_cost = np.sum((c_import * imp_vals - c_export * exp_vals) * dt_hours)
        deg_cost = np.sum(self.specs.degradation_cost_per_kwh * (ch_vals + dis_vals) * dt_hours)
        total_optimized_cost = optimized_grid_cost + deg_cost
        gross_arbitrage_savings = unmanaged_cost - optimized_grid_cost
        net_arbitrage_savings = unmanaged_cost - total_optimized_cost
        savings_pct = (net_arbitrage_savings / unmanaged_cost * 100.0) if unmanaged_cost > 0 else 0.0

        # Solar self-consumption calculation
        solar_energy_total = np.sum(P_sol * dt_hours)
        solar_exported_unmanaged = np.sum(unmanaged_exp * dt_hours)
        solar_self_unmanaged = solar_energy_total - solar_exported_unmanaged

        solar_exported_bess = np.sum(exp_vals * dt_hours)
        solar_self_bess = solar_energy_total - solar_exported_bess
        self_consumption_pct_bess = (solar_self_bess / solar_energy_total * 100.0) if solar_energy_total > 0 else 100.0
        self_consumption_pct_unmanaged = (solar_self_unmanaged / solar_energy_total * 100.0) if solar_energy_total > 0 else 100.0

        # Peak Shaving Calculation
        peak_demand_unmanaged = float(np.max(unmanaged_imp))
        peak_demand_bess = float(np.max(imp_vals))
        peak_shaved_kw = peak_demand_unmanaged - peak_demand_bess
        peak_shaved_pct = (peak_shaved_kw / peak_demand_unmanaged * 100.0) if peak_demand_unmanaged > 0 else 0.0

        schedule_dict = {
            "step": np.arange(T),
            "solar_generation_kw": np.round(P_sol, 2),
            "load_demand_kw": np.round(P_load, 2),
            "import_tariff": np.round(c_import, 4),
            "battery_charge_kw": np.round(ch_vals, 2),
            "battery_discharge_kw": np.round(dis_vals, 2),
            "battery_energy_kwh": np.round(e_vals, 2),
            "battery_soc_pct": np.round(soc_pct, 2),
            "grid_import_with_bess_kw": np.round(imp_vals, 2),
            "grid_export_with_bess_kw": np.round(exp_vals, 2),
            "grid_import_unmanaged_kw": np.round(unmanaged_imp, 2),
            "grid_export_unmanaged_kw": np.round(unmanaged_exp, 2),
        }
        if timestamps is not None:
            schedule_dict["time"] = timestamps.values

        schedule_df = pd.DataFrame(schedule_dict)

        kpis = {
            "solver_status": solver_status_str,
            "cost_without_bess": round(float(unmanaged_cost), 2),
            "cost_with_bess": round(float(total_optimized_cost), 2),
            "optimized_grid_cost": round(float(optimized_grid_cost), 2),
            "degradation_wear_cost": round(float(deg_cost), 2),
            "gross_arbitrage_savings": round(float(gross_arbitrage_savings), 2),
            "net_arbitrage_savings": round(float(net_arbitrage_savings), 2),
            "savings_percentage": round(float(savings_pct), 2),
            "peak_grid_import_without_bess_kw": round(peak_demand_unmanaged, 2),
            "peak_grid_import_with_bess_kw": round(peak_demand_bess, 2),
            "peak_demand_shaved_kw": round(float(peak_shaved_kw), 2),
            "peak_shaving_percentage": round(float(peak_shaved_pct), 2),
            "solar_self_consumption_without_bess_pct": round(float(self_consumption_pct_unmanaged), 2),
            "solar_self_consumption_with_bess_pct": round(float(self_consumption_pct_bess), 2),
            "battery_total_throughput_kwh": round(float(np.sum((ch_vals + dis_vals) * dt_hours)), 2),
            "equivalent_full_cycles": round(float(np.sum((ch_vals + dis_vals) * dt_hours) / (2 * self.specs.capacity_kwh)), 2),
        }

        return {
            "schedule_df": schedule_df,
            "kpi_summary": kpis,
            "solver_status": solver_status_str,
        }

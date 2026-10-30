"""
Smart Energy Grid & Solar Power Forecasting with Battery Optimization
Streamlit Web Application (Week 1 & Week 2 Integrated System)
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Ensure project root is available in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.data.loader import load_processed_handoff
from src.data.weather_live import fetch_live_openmeteo_forecast
from src.models.forecasting import generate_24h_ahead_solar_forecast
from src.optimization.battery_lp import BatterySpecs, TOUTariff, BatteryOptimizerLP
from src.analysis.weather_stress_test import SCENARIOS, run_full_weather_stress_suite
from src.analysis.carbon_accounting import (
    GRID_EMISSION_PROVENANCE,
    run_carbon_scenario_analysis,
    calculate_carbon_offsets,
)
from src.visualization.executive_report import generate_executive_pdf

st.set_page_config(
    page_title="Smart Solar Grid & Battery Optimization",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a professional enterprise UI
st.markdown(
    """
    <style>
    .main-header {
        font-size: 1.85rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    .sub-header {
        font-size: 0.95rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.45rem !important;
        font-weight: 600 !important;
        color: #0f172a !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        color: #64748b !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 0.75rem 1rem;
        border-radius: 6px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        font-size: 0.9rem;
        font-weight: 500;
        border-radius: 4px;
        padding: 0 16px;
    }
    .badge-hero {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e40af;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header Section
st.markdown('<div class="main-header">⚡ Smart Solar Grid & Battery Optimization</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">24-Hour AI/ML Generation Forecasting (LightGBM & Prophet) with PuLP Linear Programming Battery Arbitrage</div>',
    unsafe_allow_html=True,
)

# Sidebar Configuration
st.sidebar.markdown("### Plant Parameters")
plant_id = st.sidebar.selectbox(
    "Solar Plant",
    options=[1, 2],
    format_func=lambda x: f"Plant {x} (ID: {3418353 if x == 1 else 4135001})"
)

granularity = st.sidebar.selectbox(
    "Dataset Granularity",
    options=["15min", "15min_plant", "hourly"],
    format_func=lambda x: (
        "15-Minute Inverter Level (68k Records)" if x == "15min"
        else ("15-Minute Plant Aggregated (3.2k Records)" if x == "15min_plant"
        else "Hourly Plant Aggregated (816 Records)")
    )
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Plant Specifications")
if plant_id == 1:
    st.sidebar.markdown(
        """
        - **Location:** 14.80° N, 78.18° E
        - **Elevation:** 203 m
        - **Inverters:** 22 Units (Total ~29 MW Peak)
        - **Data Span:** 34 Days (May–June 2020)
        """
    )
else:
    st.sidebar.markdown(
        """
        - **Location:** 14.38° N, 77.50° E
        - **Elevation:** 491 m
        - **Inverters:** 22 Units (Total ~26 MW Peak)
        - **Data Span:** 34 Days (May–June 2020)
        """
    )


@st.cache_data
def get_data(pid: int, freq: str):
    try:
        return load_processed_handoff(plant_id=pid, freq=freq)
    except Exception as e:
        st.error(f"Failed to load dataset: {e}")
        return None


df_raw_loaded = get_data(plant_id, granularity)

if df_raw_loaded is not None:
    # Optional Inverter Filter if inverter-level data is loaded
    selected_inverter = "All Inverters (Plant Aggregate)"
    if "source_key" in df_raw_loaded.columns:
        inverter_list = sorted(df_raw_loaded["source_key"].unique())
        selected_inverter = st.sidebar.selectbox(
            "Inverter Unit",
            options=["All Inverters (Plant Aggregate)"] + inverter_list
        )

    # Filter or aggregate df according to inverter selection
    if selected_inverter != "All Inverters (Plant Aggregate)":
        df = df_raw_loaded[df_raw_loaded["source_key"] == selected_inverter].copy()
    elif "source_key" in df_raw_loaded.columns:
        numeric_weather_cols = [c for c in [
            "sensor_irradiation", "sensor_temperature", "module_temperature",
            "openmeteo_temperature", "humidity", "ghi", "direct_radiation", "dhi", "dni", "wind_speed_10m"
        ] if c in df_raw_loaded.columns]
        
        agg_rules = {"ac_power": "sum", "dc_power": "sum"}
        if "daily_yield" in df_raw_loaded.columns:
            agg_rules["daily_yield"] = "sum"
        for w in numeric_weather_cols:
            agg_rules[w] = "mean"

        df = df_raw_loaded.groupby("time").agg(agg_rules).reset_index()
    else:
        df = df_raw_loaded.copy()

    # Key Performance Indicators
    total_records = len(df)
    peak_ac = df["ac_power"].max() if "ac_power" in df.columns else 0.0
    avg_ac = df["ac_power"].mean() if "ac_power" in df.columns else 0.0

    time_diff_hours = 0.25 if "15min" in granularity else 1.0
    total_energy_mwh = (df["ac_power"].sum() * time_diff_hours) / 1000.0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Energy Generated", value=f"{total_energy_mwh:,.1f} MWh")
    with col2:
        st.metric(label="Peak AC Output", value=f"{peak_ac:,.1f} kW")
    with col3:
        st.metric(label="Average Generation", value=f"{avg_ac:,.1f} kW")
    with col4:
        st.metric(label="Observed Time Steps", value=f"{total_records:,}")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # Navigation Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Generation & Irradiance Analysis",
        "AI/ML Forecast Benchmarks (Week 1 & 2)",
        "🔋 Battery Arbitrage & LP Optimization (Week 2)",
        "Dataset Inspection & Export",
        "⛈️ Extreme-Weather Stress Testing (Week 4)",
        "🌱 Carbon Accounting & Executive PDF (Week 4)"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: Generation & Irradiance
    # -------------------------------------------------------------------------
    with tab1:
        st.markdown("#### Generation Timeline vs. Solar Irradiance")
        fig = go.Figure()

        # AC Power Trace
        fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["ac_power"],
            mode="lines",
            name="AC Power Output (kW)",
            line=dict(color="#2563eb", width=2),
            hovertemplate="%{x}<br>AC Power: %{y:,.1f} kW<extra></extra>"
        ))

        # Irradiance Trace (Secondary Axis)
        if "ghi" in df.columns:
            fig.add_trace(go.Scatter(
                x=df["time"],
                y=df["ghi"],
                mode="lines",
                name="Global Horizontal Irradiance (W/m²)",
                yaxis="y2",
                line=dict(color="#f59e0b", width=1.5, dash="dot"),
                hovertemplate="%{x}<br>GHI: %{y:,.1f} W/m²<extra></extra>"
            ))
            fig.update_layout(
                yaxis2=dict(
                    title="GHI (W/m²)",
                    title_font=dict(size=12, color="#64748b"),
                    overlaying="y",
                    side="right",
                    showgrid=False
                )
            )

        fig.update_layout(
            xaxis=dict(
                title="Date & Time",
                title_font=dict(size=12, color="#64748b"),
                rangeslider=dict(visible=True, thickness=0.06),
                type="date"
            ),
            yaxis=dict(
                title="AC Power Output (kW)",
                title_font=dict(size=12, color="#64748b"),
                gridcolor="#f1f5f9"
            ),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=30, b=40),
            template="plotly_white",
            height=460
        )
        st.plotly_chart(fig, use_container_width=True)

        # Diurnal Average Generation Profile
        st.markdown("#### Mean Diurnal Profile (Hour of Day)")
        df["hour"] = pd.to_datetime(df["time"]).dt.hour
        hourly_summary = df.groupby("hour")["ac_power"].agg(["mean", "std", "max"]).reset_index()

        fig_diurnal = go.Figure()
        fig_diurnal.add_trace(go.Scatter(
            x=hourly_summary["hour"],
            y=hourly_summary["mean"],
            mode="lines+markers",
            name="Mean AC Power (kW)",
            line=dict(color="#2563eb", width=2.5),
            marker=dict(size=6)
        ))
        fig_diurnal.add_trace(go.Scatter(
            x=hourly_summary["hour"],
            y=hourly_summary["max"],
            mode="lines",
            name="Peak Observed Output (kW)",
            line=dict(color="#94a3b8", width=1.5, dash="dash")
        ))
        fig_diurnal.update_layout(
            xaxis=dict(title="Hour of Day (IST)", tickmode="linear", tick0=0, dtick=2),
            yaxis=dict(title="AC Power (kW)", gridcolor="#f1f5f9"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=30, b=40),
            template="plotly_white",
            height=340
        )
        st.plotly_chart(fig_diurnal, use_container_width=True)

    # -------------------------------------------------------------------------
    # TAB 2: Forecast Benchmarks (Week 1 Baselines & Week 2 Models)
    # -------------------------------------------------------------------------
    with tab2:
        st.markdown("#### Out-of-Sample 7-Day Forecasting Leaderboard")
        st.caption(
            "Evaluated out-of-sample across the final 7 consecutive days (~14,700 test observations per plant). "
            "Nighttime zero-inflation is physically enforced when solar elevation ≤ 0° or GHI ≤ 1.0 W/m²."
        )

        metrics_week2_file = root_dir / "reports" / "week2_forecasting_metrics_summary.csv"
        metrics_week1_file = root_dir / "reports" / "week1_baseline_metrics_summary.csv"
        
        metrics_file = metrics_week2_file if metrics_week2_file.exists() else metrics_week1_file

        if metrics_file.exists():
            summary_df = pd.read_csv(metrics_file)
            plant_metrics = summary_df[summary_df["plant_id"] == plant_id].drop(columns=["plant_id"])
            plant_metrics = plant_metrics.rename(columns={
                "model": "Model",
                "daylight_rmse": "Daylight RMSE (kW)",
                "daylight_mape_pct": "Daylight MAPE (%)",
                "daylight_mae": "Daylight MAE (kW)",
                "daylight_r2": "Daylight R²",
                "rmse_overall": "Overall RMSE (kW)",
                "r2_overall": "Overall R²",
                "daylight_nrmse_pct": "Daylight nRMSE (%)"
            })

            st.dataframe(
                plant_metrics.style.format({
                    "Daylight RMSE (kW)": "{:,.2f}",
                    "Daylight MAPE (%)": "{:.2f}%",
                    "Daylight MAE (kW)": "{:,.2f}",
                    "Daylight R²": "{:.4f}",
                    "Overall RMSE (kW)": "{:,.2f}",
                    "Overall R²": "{:.4f}",
                    "Daylight nRMSE (%)": "{:.2f}%"
                }),
                use_container_width=True,
                hide_index=True
            )

        # Plot Predictions
        pred_w2_file = root_dir / "reports" / f"plant{plant_id}_week2_forecasting_predictions.csv"
        pred_w1_file = root_dir / "reports" / f"plant{plant_id}_week1_baseline_predictions.csv"
        pred_file = pred_w2_file if pred_w2_file.exists() else pred_w1_file

        if pred_file.exists():
            df_preds_raw = pd.read_csv(pred_file)
            df_preds_raw["time"] = pd.to_datetime(df_preds_raw["time"])

            if "source_key" in df_preds_raw.columns and selected_inverter != "All Inverters (Plant Aggregate)":
                df_preds = df_preds_raw[df_preds_raw["source_key"] == selected_inverter].sort_values("time")
                chart_sub = f"Showing individual inverter output for {selected_inverter}."
            elif "source_key" in df_preds_raw.columns:
                num_cols = [c for c in df_preds_raw.columns if c not in ["time", "source_key"]]
                df_preds = df_preds_raw.groupby("time")[num_cols].sum().reset_index().sort_values("time")
                chart_sub = "Showing total plant aggregate output (sum of all 22 inverters)."
            else:
                df_preds = df_preds_raw.sort_values("time")
                chart_sub = "Showing plant-level output."

            st.markdown(f"##### Test Horizon Predictions vs. Ground Truth ({chart_sub})")

            fig_pred = go.Figure()
            # Actual Ground Truth
            fig_pred.add_trace(go.Scatter(
                x=df_preds["time"],
                y=df_preds["actual_ac_power"],
                mode="lines",
                name="Actual Power",
                line=dict(color="#0f172a", width=2.5),
                hovertemplate="%{x}<br>Actual: %{y:,.1f} kW<extra></extra>"
            ))

            # LightGBM (Week 2 Hero)
            if "pred_lightgbm" in df_preds.columns:
                fig_pred.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_lightgbm"],
                    mode="lines",
                    name="LightGBM (GBDT)",
                    line=dict(color="#10b981", width=2.0),
                    hovertemplate="%{x}<br>LightGBM: %{y:,.1f} kW<extra></extra>"
                ))

            # XGBoost (Week 2 GBDT)
            if "pred_xgboost" in df_preds.columns:
                fig_pred.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_xgboost"],
                    mode="lines",
                    name="XGBoost (GBDT)",
                    line=dict(color="#f97316", width=1.8),
                    hovertemplate="%{x}<br>XGBoost: %{y:,.1f} kW<extra></extra>"
                ))

            # Ridge Regression (Week 1 Baseline)
            if "pred_ridge" in df_preds.columns:
                fig_pred.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_ridge"],
                    mode="lines",
                    name="Ridge Regression",
                    line=dict(color="#2563eb", width=1.75, dash="dash"),
                    hovertemplate="%{x}<br>Ridge: %{y:,.1f} kW<extra></extra>"
                ))
            elif "pred_ridge_regression" in df_preds.columns:
                fig_pred.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_ridge_regression"],
                    mode="lines",
                    name="Ridge Regression",
                    line=dict(color="#2563eb", width=1.75, dash="dash"),
                    hovertemplate="%{x}<br>Ridge: %{y:,.1f} kW<extra></extra>"
                ))

            # Prophet (Week 2 Additive TS)
            if "pred_prophet" in df_preds.columns:
                fig_pred.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_prophet"],
                    mode="lines",
                    name="Facebook Prophet",
                    line=dict(color="#8b5cf6", width=1.5, dash="dot"),
                    hovertemplate="%{x}<br>Prophet: %{y:,.1f} kW<extra></extra>"
                ))

            # Persistence Benchmark (24h Lag)
            if "pred_persistence" in df_preds.columns:
                fig_pred.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_persistence"],
                    mode="lines",
                    name="Persistence (24h Lag)",
                    line=dict(color="#94a3b8", width=1.2, dash="dot"),
                    hovertemplate="%{x}<br>Persistence: %{y:,.1f} kW<extra></extra>"
                ))

            fig_pred.update_layout(
                xaxis=dict(
                    title="Timestamp",
                    title_font=dict(size=12, color="#64748b"),
                    rangeslider=dict(visible=True, thickness=0.06),
                    type="date"
                ),
                yaxis=dict(
                    title="AC Power (kW)",
                    title_font=dict(size=12, color="#64748b"),
                    gridcolor="#f1f5f9"
                ),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=30, b=40),
                template="plotly_white",
                height=480
            )
            st.plotly_chart(fig_pred, use_container_width=True)

            # Feature Importance section
            feat_file = root_dir / "reports" / f"plant{plant_id}_lightgbm_feature_importance.csv"
            if feat_file.exists():
                st.markdown("##### 🌳 LightGBM Feature Importance (Split Gain)")
                df_imp = pd.read_csv(feat_file)
                fig_imp = go.Figure(go.Bar(
                    x=df_imp["importance"][:12],
                    y=df_imp["feature"][:12],
                    orientation="h",
                    marker=dict(color="#3b82f6"),
                ))
                fig_imp.update_layout(
                    yaxis=dict(autorange="reversed"),
                    xaxis=dict(title="Importance (Split Count)"),
                    margin=dict(l=40, r=40, t=20, b=40),
                    height=360,
                    template="plotly_white"
                )
                st.plotly_chart(fig_imp, use_container_width=True)

        # ---------------------------------------------------------------------
        # Live Open-Meteo Weather & Genuine 24-Hour Solar Forecast
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 🛰️ Live Open-Meteo Weather & Genuine 24-Hour Solar Forecast")
        st.caption(
            "Real-time meteorological telemetry from Open-Meteo Weather API for configured plant coordinates. "
            "Exogenous weather variables drive genuine upcoming 24-hour predictions across LightGBM, XGBoost, and Prophet."
        )

        try:
            live_w = fetch_live_openmeteo_forecast(plant_id=plant_id)
            cond = live_w.get("current_conditions", {})
            w_source = live_w.get("data_source", "Open-Meteo")
            is_live = live_w.get("is_live", False)
            status_badge = "🟢 Live API Telemetry" if is_live else "🟡 Historical Fallback"

            wcol1, wcol2, wcol3, wcol4 = st.columns(4)
            with wcol1:
                st.metric("Weather Feed", status_badge, help=w_source)
            with wcol2:
                st.metric("Ambient Temp", f"{cond.get('temperature_c', 0.0):.1f} °C", help=f"Recorded: {cond.get('time')}")
            with wcol3:
                st.metric("Solar GHI", f"{cond.get('ghi_wm2', 0.0):.1f} W/m²")
            with wcol4:
                st.metric("Cloud Cover", f"{cond.get('cloud_cover_pct', 0.0):.0f}%", help=f"Wind: {cond.get('wind_speed_kmh', 0.0):.1f} km/h")

            live_fc = generate_24h_ahead_solar_forecast(plant_id=plant_id, horizon_hours=24)
            tl = live_fc.get("timeline", [])
            if tl:
                df_tl = pd.DataFrame(tl)
                df_tl["time_dt"] = pd.to_datetime(df_tl["timestamp"])

                fig_future = go.Figure()
                # 90% Uncertainty Bound Envelope
                fig_future.add_trace(go.Scatter(
                    x=df_tl["time_dt"],
                    y=df_tl["upper_bound_kw"],
                    mode="lines",
                    line=dict(width=0),
                    showlegend=False,
                    hoverinfo="skip"
                ))
                fig_future.add_trace(go.Scatter(
                    x=df_tl["time_dt"],
                    y=df_tl["lower_bound_kw"],
                    mode="lines",
                    line=dict(width=0),
                    fill="tonexty",
                    fillcolor="rgba(16, 185, 129, 0.15)",
                    name="90% Confidence Interval",
                    hoverinfo="skip"
                ))
                # Primary LightGBM Forecast
                fig_future.add_trace(go.Scatter(
                    x=df_tl["time_dt"],
                    y=df_tl["lightgbm_kw"],
                    mode="lines+markers",
                    name="LightGBM (GBDT)",
                    line=dict(color="#10b981", width=2.5),
                    marker=dict(size=5),
                    hovertemplate="%{x}<br>LightGBM: %{y:,.1f} kW<extra></extra>"
                ))
                # XGBoost
                fig_future.add_trace(go.Scatter(
                    x=df_tl["time_dt"],
                    y=df_tl["xgboost_kw"],
                    mode="lines",
                    name="XGBoost (GBDT)",
                    line=dict(color="#f97316", width=2.0, dash="dash"),
                    hovertemplate="%{x}<br>XGBoost: %{y:,.1f} kW<extra></extra>"
                ))
                # Prophet
                fig_future.add_trace(go.Scatter(
                    x=df_tl["time_dt"],
                    y=df_tl["prophet_kw"],
                    mode="lines",
                    name="Facebook Prophet",
                    line=dict(color="#8b5cf6", width=1.5, dash="dot"),
                    hovertemplate="%{x}<br>Prophet: %{y:,.1f} kW<extra></extra>"
                ))
                fig_future.update_layout(
                    title=f"Upcoming 24-Hour Solar Generation Forecast ({live_fc.get('forecast_start')} to {live_fc.get('forecast_end')})",
                    xaxis=dict(title="Future Timestamp (Asia/Kolkata)", type="date"),
                    yaxis=dict(title="Forecast AC Power (kW)", gridcolor="#f1f5f9"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    template="plotly_white",
                    height=360,
                    margin=dict(l=40, r=40, t=40, b=40),
                )
                st.plotly_chart(fig_future, use_container_width=True)
                st.info(f"💡 Forecast horizon totals: **{live_fc['kpis']['total_predicted_energy_mwh']:.2f} MWh** estimated generation with **{live_fc['kpis']['peak_predicted_kw']:,.1f} kW** peak output across **{live_fc['kpis']['daylight_hours']} daylight hours**.")
        except Exception as e:
            st.warning(f"Could not load live weather forecast: {e}")

    # -------------------------------------------------------------------------
    # TAB 3: PuLP Battery Arbitrage & Optimization (Week 2 Hero Tab)
    # -------------------------------------------------------------------------
    with tab3:
        st.markdown("#### 🔋 Battery Energy Storage System (BESS) Arbitrage Optimizer")
        st.caption(
            "Solves a 24-Hour Linear Programming (LP) optimization problem using PuLP. "
            "Charges battery during low-tariff solar overgeneration hours and discharges during evening peak hours."
        )
        st.info(
            "📌 **Assumptions & Disclaimers:** Baseline facility demand is a calibrated synthetic scenario scaled to plant capacity (actual utility telemetry unavailable). "
            "TOU rates are representative benchmark assumptions ($/kWh or INR ₹ equivalent scenario), not actual plant billing records."
        )

        # Dispatch Solar Profile Selection
        st.markdown("##### ☀️ Solar Dispatch Source")
        dispatch_mode = st.radio(
            "Select Generation Input Profile for Optimization",
            options=["Upcoming 24-Hour Solar Forecast (Live Open-Meteo)", "Historical Baseline Day (Last 24h Slice)"],
            horizontal=True,
            help="Choose whether to optimize day-ahead battery dispatch on live upcoming solar forecast or historical recorded generation."
        )

        use_future = "Upcoming 24-Hour" in dispatch_mode
        day_slice_solar = None
        day_slice_time = None
        data_source_label = ""

        if use_future:
            try:
                fc_data = generate_24h_ahead_solar_forecast(plant_id=plant_id, horizon_hours=24)
                tl = fc_data.get("timeline", [])
                if len(tl) == 24:
                    day_slice_solar = np.array([float(s["selected_solar_kw"]) for s in tl], dtype=float)
                    day_slice_time = pd.to_datetime([s["timestamp"] for s in tl])
                    data_source_label = f"Upcoming 24-Hour Forecast ({fc_data.get('data_source', 'Live Open-Meteo')})"
            except Exception as e:
                st.warning(f"Failed to generate future forecast ({e}), falling back to historical baseline.")
                use_future = False

        if day_slice_solar is None:
            df_hourly_all = get_data(plant_id, "hourly")
            if df_hourly_all is not None:
                day_slice = df_hourly_all.tail(24).copy().reset_index(drop=True)
                day_slice_solar = day_slice["ac_power"].values
                day_slice_time = pd.to_datetime(day_slice["time"])
                data_source_label = "Historical Hourly Generation (24-Hour Baseline Slice)"

        if day_slice_solar is not None:
            st.caption(f"📅 Active dispatch horizon: **{data_source_label}** | Duration: 24 Hours")

        # Battery Configuration Controls
        bcol1, bcol2, bcol3, bcol4 = st.columns(4)
        with bcol1:
            batt_cap_mwh = st.slider("Battery Storage Capacity (MWh)", min_value=1.0, max_value=30.0, value=10.0, step=1.0)
            batt_cap_kwh = batt_cap_mwh * 1000.0
        with bcol2:
            max_p_mw = st.slider("Max Inverter Power (MW)", min_value=0.5, max_value=15.0, value=5.0, step=0.5)
            max_p_kw = max_p_mw * 1000.0
        with bcol3:
            round_trip_eff = st.slider("Round-Trip Efficiency (%)", min_value=75.0, max_value=98.0, value=90.25, step=0.5)
            one_way_eff = float(np.sqrt(round_trip_eff / 100.0))
        with bcol4:
            initial_soc_pct = st.slider("Initial SoC (%)", min_value=10.0, max_value=80.0, value=20.0, step=5.0)

        # TOU Tariff Settings
        st.markdown("##### Time-of-Use (TOU) Tariff Schedule")
        tcol1, tcol2, tcol3, tcol4 = st.columns(4)
        with tcol1:
            off_peak_price = st.number_input("Off-Peak Rate ($/kWh)", min_value=0.01, max_value=0.50, value=0.05, step=0.01)
        with tcol2:
            normal_price = st.number_input("Normal / Shoulder Rate ($/kWh)", min_value=0.01, max_value=0.50, value=0.10, step=0.01)
        with tcol3:
            peak_price = st.number_input("Evening Peak Rate (17:00-21:00) ($/kWh)", min_value=0.05, max_value=1.00, value=0.25, step=0.02)
        with tcol4:
            export_rate = st.number_input("Grid Solar Export Feed-In ($/kWh)", min_value=0.00, max_value=0.30, value=0.04, step=0.01)

        if day_slice_solar is not None:
            # Setup optimizer
            b_specs = BatterySpecs(
                capacity_kwh=batt_cap_kwh,
                max_charge_kw=max_p_kw,
                max_discharge_kw=max_p_kw,
                charge_efficiency=one_way_eff,
                discharge_efficiency=one_way_eff,
                soc_min=0.10,
                soc_max=0.90,
                soc_initial=initial_soc_pct / 100.0,
                degradation_cost_per_kwh=0.005,
            )
            b_tariff = TOUTariff(
                off_peak_rate=off_peak_price,
                normal_rate=normal_price,
                peak_rate=peak_price,
                export_feedin_rate=export_rate,
            )

            b_optimizer = BatteryOptimizerLP(specs=b_specs, tariff=b_tariff)
            opt_res = b_optimizer.optimize_dispatch(
                solar_kw=day_slice_solar,
                timestamps=day_slice_time,
                dt_hours=1.0,
                enforce_terminal_soc=True,
            )

            kpis = opt_res["kpi_summary"]
            sched_df = opt_res["schedule_df"]

            # Display Optimization KPIs
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            kcol1, kcol2, kcol3, kcol4 = st.columns(4)
            with kcol1:
                st.metric("Net Arbitrage Savings", f"${kpis['net_arbitrage_savings']:,.2f}", delta=f"{kpis['savings_percentage']:.1f}% reduction")
            with kcol2:
                st.metric("Cost Without BESS", f"${kpis['cost_without_bess']:,.2f}")
            with kcol3:
                st.metric("Cost With BESS", f"${kpis['cost_with_bess']:,.2f}")
            with kcol4:
                st.metric("Solar Self-Consumption", f"{kpis['solar_self_consumption_with_bess_pct']:.1f}%", delta=f"+{kpis['solar_self_consumption_with_bess_pct'] - kpis['solar_self_consumption_without_bess_pct']:.1f}%")

            # Plotly Chart: The Duck Curve Mitigation
            st.markdown("##### 🦆 Duck Curve & Grid Load Shifting (Unmanaged vs. BESS Managed)")
            fig_duck = go.Figure()
            
            # Solar generation
            fig_duck.add_trace(go.Scatter(
                x=sched_df["step"],
                y=sched_df["solar_generation_kw"] / 1000.0,
                mode="lines",
                name="Solar Output (MW)",
                line=dict(color="#f59e0b", width=2.5),
                fill="tozeroy",
                fillcolor="rgba(245, 158, 11, 0.15)"
            ))

            # Baseline load (Simulated)
            fig_duck.add_trace(go.Scatter(
                x=sched_df["step"],
                y=sched_df["load_demand_kw"] / 1000.0,
                mode="lines",
                name="Baseline Demand [Simulated] (MW)",
                line=dict(color="#64748b", width=2, dash="dash")
            ))

            # Unmanaged Grid Import
            fig_duck.add_trace(go.Scatter(
                x=sched_df["step"],
                y=sched_df["grid_import_unmanaged_kw"] / 1000.0,
                mode="lines",
                name="Unmanaged Grid Import (Duck Curve Peak)",
                line=dict(color="#ef4444", width=2.0)
            ))

            # Optimized Grid Import with BESS
            fig_duck.add_trace(go.Scatter(
                x=sched_df["step"],
                y=sched_df["grid_import_with_bess_kw"] / 1000.0,
                mode="lines",
                name="Optimized Grid Import (With BESS)",
                line=dict(color="#10b981", width=2.5)
            ))

            fig_duck.update_layout(
                xaxis=dict(title="Hour of Day (0 to 23)", tickmode="linear", tick0=0, dtick=2),
                yaxis=dict(title="Power (MW)", gridcolor="#f1f5f9"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=30, b=40),
                template="plotly_white",
                height=380
            )
            st.plotly_chart(fig_duck, use_container_width=True)

            # Plotly Chart: Battery Charge, Discharge, and SoC Evolution
            st.markdown("##### ⚡ Battery Power Dispatch & State of Charge (SoC %)")
            fig_batt = make_subplots(specs=[[{"secondary_y": True}]])

            # Charging Power (Negative or positive bar)
            fig_batt.add_trace(go.Bar(
                x=sched_df["step"],
                y=sched_df["battery_charge_kw"] / 1000.0,
                name="Charging Power (MW)",
                marker_color="#3b82f6"
            ), secondary_y=False)

            # Discharging Power
            fig_batt.add_trace(go.Bar(
                x=sched_df["step"],
                y=-sched_df["battery_discharge_kw"] / 1000.0,
                name="Discharging Power (MW)",
                marker_color="#f97316"
            ), secondary_y=False)

            # Battery State of Charge (%)
            fig_batt.add_trace(go.Scatter(
                x=sched_df["step"],
                y=sched_df["battery_soc_pct"],
                mode="lines+markers",
                name="Battery SoC (%)",
                line=dict(color="#8b5cf6", width=2.5),
                marker=dict(size=6)
            ), secondary_y=True)

            fig_batt.update_yaxes(title_text="Battery Power [Charge(+) / Discharge(-)] (MW)", secondary_y=False, gridcolor="#f1f5f9")
            fig_batt.update_yaxes(title_text="State of Charge (SoC %)", secondary_y=True, range=[0, 100])
            fig_batt.update_xaxes(title_text="Hour of Day", tickmode="linear", tick0=0, dtick=2)
            fig_batt.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=30, b=40),
                template="plotly_white",
                height=380
            )
            st.plotly_chart(fig_batt, use_container_width=True)

            # Dispatch Schedule Table
            with st.expander("🔍 View Detailed 24-Hour Hour-by-Hour Dispatch Schedule"):
                st.dataframe(sched_df, use_container_width=True, hide_index=True)
                csv_sched = sched_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download 24-Hour Dispatch Schedule CSV",
                    data=csv_sched,
                    file_name="battery_optimal_dispatch_24h.csv",
                    mime="text/csv"
                )

    # -------------------------------------------------------------------------
    # TAB 4: Dataset Records & Export
    # -------------------------------------------------------------------------
    with tab4:
        st.markdown("#### Processed Dataset Records")
        st.caption(f"Showing records for Plant {plant_id} ({granularity} resolution).")

        display_cols = [c for c in [
            "time", "ac_power", "dc_power", "ac_energy_kwh_est",
            "sensor_irradiation", "sensor_temperature", "module_temperature",
            "openmeteo_temperature", "humidity", "ghi", "cloud"
        ] if c in df.columns]

        st.dataframe(df[display_cols].head(100), use_container_width=True, hide_index=True)

        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Filtered Dataset as CSV",
            data=csv_data,
            file_name=f"plant_{plant_id}_{granularity}_data.csv",
            mime="text/csv"
        )

    # -------------------------------------------------------------------------
    # TAB 5: Extreme-Weather Stress Testing (Week 4)
    # -------------------------------------------------------------------------
    with tab5:
        st.markdown("#### ⛈️ Extreme-Weather Stress Testing & Battery Resilience")
        st.caption(
            "Simulates calibrated meteorological disruptions (heavy cloud cover, prolonged monsoon low, "
            "sudden midday drop, multi-day deficit, post-storm recovery) to benchmark forecast error spikes "
            "and PuLP battery storage resilience."
        )

        reports_dir = root_dir / "reports"
        stress_summary_csv = reports_dir / "week4_weather_stress_summary.csv"
        if not stress_summary_csv.exists():
            with st.spinner("Executing Extreme-Weather Stress Testing Suite..."):
                run_full_weather_stress_suite(plant_id=plant_id)

        if stress_summary_csv.exists():
            df_stress_summary = pd.read_csv(stress_summary_csv)

            scenario_names = df_stress_summary["scenario_name"].tolist()
            scenario_labels = df_stress_summary["scenario_label"].tolist()
            selected_label = st.selectbox("Select Weather Stress Scenario", options=scenario_labels)
            selected_row = df_stress_summary[df_stress_summary["scenario_label"] == selected_label].iloc[0]

            # Scenario description
            sc_meta = SCENARIOS.get(selected_row["scenario_name"], {})
            st.info(f"**Scenario Profile:** {sc_meta.get('description', '')}")

            # Metric Cards
            s_col1, s_col2, s_col3, s_col4 = st.columns(4)
            with s_col1:
                st.metric("Total Solar Generation", f"{selected_row['total_solar_generation_mwh']:.1f} MWh")
            with s_col2:
                st.metric("Ridge Daylight RMSE", f"{selected_row['ridge_daylight_rmse_kw']:.1f} kW")
            with s_col3:
                st.metric("LightGBM Daylight RMSE", f"{selected_row['lgb_daylight_rmse_kw']:.1f} kW")
            with s_col4:
                st.metric("Net Battery Arbitrage", f"₹{selected_row['net_arbitrage_savings']:,.0f}")

            # Plotly Scenario Comparison Bar Chart
            fig_stress = go.Figure()
            fig_stress.add_trace(go.Bar(
                x=df_stress_summary["scenario_label"],
                y=df_stress_summary["total_solar_generation_mwh"],
                name="Solar Generation (MWh)",
                marker_color="#f59e0b"
            ))
            fig_stress.add_trace(go.Bar(
                x=df_stress_summary["scenario_label"],
                y=df_stress_summary["net_arbitrage_savings"] / 1000.0,
                name="Net Arbitrage (₹k)",
                marker_color="#10b981"
            ))
            fig_stress.update_layout(
                title="Cross-Scenario Generation & Battery Economic Resilience",
                barmode="group",
                template="plotly_white",
                height=350,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_stress, use_container_width=True)

            # Scenario Matrix Table
            st.markdown("##### Comprehensive Stress Matrix")
            st.dataframe(df_stress_summary, use_container_width=True, hide_index=True)

            st.download_button(
                label="Download Weather Stress Summary CSV",
                data=df_stress_summary.to_csv(index=False).encode("utf-8"),
                file_name="week4_weather_stress_summary.csv",
                mime="text/csv"
            )

    # -------------------------------------------------------------------------
    # TAB 6: Carbon Accounting & Executive PDF (Week 4)
    # -------------------------------------------------------------------------
    with tab6:
        st.markdown("#### 🌱 Carbon-Offset Accounting & Executive PDF Report")
        st.caption(
            "Calculates operational grid emissions avoided by solar generation and battery load shifting, "
            "benchmarked against the Central Electricity Authority (CEA) Baseline Database Version 19.0."
        )

        st.success(
            f"**Regulatory Provenance:** {GRID_EMISSION_PROVENANCE['source']} "
            f"({GRID_EMISSION_PROVENANCE['version']}) — Default National Weighted Average: "
            f"**{GRID_EMISSION_PROVENANCE['national_weighted_average_factor_kg_per_kwh']} kg CO2e/kWh** "
            f"(Thermal Marginal: {GRID_EMISSION_PROVENANCE['thermal_marginal_factor_kg_per_kwh']} kg CO2e/kWh)."
        )

        carbon_summary_csv = reports_dir / "week4_carbon_summary.csv"
        if not carbon_summary_csv.exists():
            with st.spinner("Executing Carbon Accounting Suite..."):
                run_carbon_scenario_analysis(plant_id=plant_id)

        if carbon_summary_csv.exists():
            df_carbon = pd.read_csv(carbon_summary_csv)

            # Interactive emission factor slider
            st.markdown("##### Interactive Grid Emission Factor Tuning")
            user_ef = st.slider(
                "Grid Emission Factor (kg CO2e / kWh)",
                min_value=0.30,
                max_value=1.20,
                value=0.716,
                step=0.005,
                help="Adjust to simulate different grid generation mixes."
            )

            # Compute offsets dynamically
            base_mwh = 50.0
            daily_co2_tonnes = (base_mwh * 1000.0 * user_ef) / 1000.0
            annual_co2_tonnes = daily_co2_tonnes * 365.0
            lifetime_co2_tonnes = annual_co2_tonnes * 25.0

            c_col1, c_col2, c_col3, c_col4 = st.columns(4)
            with c_col1:
                st.metric("Grid Emission Factor", f"{user_ef:.3f} kg/kWh")
            with c_col2:
                st.metric("Daily Avoided CO2", f"{daily_co2_tonnes:.1f} Tonnes")
            with c_col3:
                st.metric("Annual Avoided CO2", f"{annual_co2_tonnes:,.0f} Tonnes")
            with c_col4:
                st.metric("25-Yr Lifetime Abatement", f"{lifetime_co2_tonnes/1000.0:,.1f}k Tonnes")

            st.markdown("##### Grid Intensity Sensitivity Matrix")
            st.dataframe(df_carbon, use_container_width=True, hide_index=True)

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        st.markdown("##### 📄 Executive Technical PDF Report")
        st.caption("Generates a publication-grade, 6-page comprehensive executive report using ReportLab.")

        pdf_path = reports_dir / f"executive_report_plant{plant_id}.pdf"
        col_gen, col_down = st.columns([1, 1])

        with col_gen:
            if st.button("Generate / Regenerate Executive PDF Report", type="primary"):
                with st.spinner("Compiling 6-page executive report..."):
                    pdf_path = generate_executive_pdf(plant_id=plant_id)
                    st.success(f"Report compiled successfully! ({pdf_path.stat().st_size / 1024:.1f} KB)")

        with col_down:
            if pdf_path.exists():
                with open(pdf_path, "rb") as f_pdf:
                    st.download_button(
                        label="📥 Download Executive Technical PDF",
                        data=f_pdf.read(),
                        file_name=f"Solar_Plant_{plant_id}_Executive_Report.pdf",
                        mime="application/pdf"
                    )
            else:
                st.info("Click 'Generate / Regenerate' to compile the PDF report.")

else:
    st.error("Processed data file could not be found. Please ensure 'data/processed/' contains the required CSV files.")

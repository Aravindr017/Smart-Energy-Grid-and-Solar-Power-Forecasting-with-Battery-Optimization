"""
Smart Energy Grid & Solar Power Forecasting with Battery Optimization
Streamlit Web Application
"""

import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Ensure project root is available in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.data.loader import load_processed_handoff

st.set_page_config(
    page_title="Solar Generation Forecasting System",
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
    </style>
    """,
    unsafe_allow_html=True,
)

# Header Section
st.markdown('<div class="main-header">Solar Generation Forecasting & Grid Optimization</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Plant Generation Analytics, Weather Irradiance Correlation, and Day-Ahead Forecasting Benchmarks</div>',
    unsafe_allow_html=True,
)

# Sidebar Configuration
st.sidebar.markdown("### Parameters")
plant_id = st.sidebar.selectbox(
    "Solar Plant",
    options=[1, 2],
    format_func=lambda x: f"Plant {x} (ID: {3418353 if x == 1 else 4135001})"
)
granularity = st.sidebar.selectbox(
    "Temporal Resolution",
    options=["hourly", "15min_plant"],
    format_func=lambda x: "Hourly Aggregation" if x == "hourly" else "15-Minute Resolution"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Plant Specifications")
if plant_id == 1:
    st.sidebar.markdown(
        """
        - **Location:** 14.80° N, 78.18° E
        - **Elevation:** 203 m
        - **Inverters:** 22 Units
        - **Data Span:** 34 Days (May–June 2020)
        """
    )
else:
    st.sidebar.markdown(
        """
        - **Location:** 14.38° N, 77.50° E
        - **Elevation:** 491 m
        - **Inverters:** 22 Units
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


df = get_data(plant_id, granularity)

if df is not None:
    # Key Performance Indicators
    total_records = len(df)
    peak_ac = df["ac_power"].max() if "ac_power" in df.columns else 0.0
    avg_ac = df["ac_power"].mean() if "ac_power" in df.columns else 0.0

    # Total estimated energy in MWh
    if "ac_energy_kwh_est" in df.columns:
        total_energy_mwh = df["ac_energy_kwh_est"].sum() / 1000.0
    else:
        # 1-hour interval approximation
        total_energy_mwh = (df["ac_power"].sum() * (1.0 if granularity == "hourly" else 0.25)) / 1000.0

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
    tab1, tab2, tab3 = st.tabs([
        "Generation & Irradiance Analysis",
        "Forecast Model Benchmarks",
        "Dataset Inspection"
    ])

    # TAB 1: Generation & Irradiance
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
            height=480
        )
        st.plotly_chart(fig, use_container_width=True)

        # Diurnal Average Generation Profile
        st.markdown("#### Mean Diurnal Profile (24-Hour Cycle)")
        df_diurnal = df.copy()
        df_diurnal["hour"] = pd.to_datetime(df_diurnal["time"]).dt.hour
        hourly_summary = df_diurnal.groupby("hour").agg(
            mean_ac=("ac_power", "mean"),
            max_ac=("ac_power", "max"),
            min_ac=("ac_power", "min")
        ).reset_index()

        fig_diurnal = go.Figure()
        fig_diurnal.add_trace(go.Scatter(
            x=hourly_summary["hour"],
            y=hourly_summary["max_ac"],
            mode="lines",
            name="Maximum Output",
            line=dict(color="#cbd5e1", width=1),
            showlegend=False
        ))
        fig_diurnal.add_trace(go.Scatter(
            x=hourly_summary["hour"],
            y=hourly_summary["min_ac"],
            mode="lines",
            name="Minimum Output",
            fill="tonexty",
            fillcolor="rgba(226, 232, 240, 0.5)",
            line=dict(color="#cbd5e1", width=1),
            showlegend=False
        ))
        fig_diurnal.add_trace(go.Scatter(
            x=hourly_summary["hour"],
            y=hourly_summary["mean_ac"],
            mode="lines+markers",
            name="Mean Generation (kW)",
            line=dict(color="#0f172a", width=2.5),
            marker=dict(size=5)
        ))
        fig_diurnal.update_layout(
            xaxis=dict(title="Hour of Day (0–23)", dtick=1, gridcolor="#f1f5f9"),
            yaxis=dict(title="AC Power (kW)", gridcolor="#f1f5f9"),
            margin=dict(l=40, r=40, t=20, b=40),
            template="plotly_white",
            height=320
        )
        st.plotly_chart(fig_diurnal, use_container_width=True)

    # TAB 2: Forecast Benchmarks
    with tab2:
        st.markdown("#### Out-of-Sample Evaluation: Actual Generation vs. Baseline Models")
        st.caption(
            "Evaluation performed over the final 7 consecutive days (168 hourly time steps). "
            "Nighttime zero-inflation is strictly enforced during non-generating hours."
        )

        metrics_file = root_dir / "reports" / "week1_baseline_metrics_summary.csv"
        pred_file = root_dir / "reports" / f"plant{plant_id}_week1_baseline_predictions.csv"

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

        if pred_file.exists():
            df_preds = pd.read_csv(pred_file)
            df_preds["time"] = pd.to_datetime(df_preds["time"])

            fig_pred = go.Figure()
            fig_pred.add_trace(go.Scatter(
                x=df_preds["time"],
                y=df_preds["actual_ac_power"],
                mode="lines",
                name="Actual Power Output",
                line=dict(color="#0f172a", width=2.5),
                hovertemplate="%{x}<br>Actual: %{y:,.1f} kW<extra></extra>"
            ))
            if "pred_ridge_regression" in df_preds.columns:
                fig_pred.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_ridge_regression"],
                    mode="lines",
                    name="Ridge Regression Baseline",
                    line=dict(color="#2563eb", width=1.75, dash="dash"),
                    hovertemplate="%{x}<br>Ridge: %{y:,.1f} kW<extra></extra>"
                ))
            if "pred_linear_regression" in df_preds.columns:
                fig_pred.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_linear_regression"],
                    mode="lines",
                    name="Linear Regression Baseline",
                    line=dict(color="#10b981", width=1.5, dash="dot"),
                    hovertemplate="%{x}<br>Linear: %{y:,.1f} kW<extra></extra>"
                ))
            if "pred_persistence_(24h_lag)" in df_preds.columns:
                fig_pred.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_persistence_(24h_lag)"],
                    mode="lines",
                    name="Persistence (24h Lag)",
                    line=dict(color="#94a3b8", width=1.25, dash="dot"),
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
        else:
            st.warning("Prediction report not found. Execute 'python run_all.py' to generate baseline predictions.")

    # TAB 3: Dataset Records
    with tab3:
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
else:
    st.error("Processed data file could not be found. Please ensure 'data/processed/' contains the required CSV files.")

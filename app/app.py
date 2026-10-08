"""
Smart Energy Grid & Solar Power Forecasting with Battery Optimization
Streamlit Web Application Entrypoint
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.data.loader import load_processed_handoff

st.set_page_config(
    page_title="Smart Solar Grid & Battery Optimization",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚡ Smart Energy Grid & Solar Forecasting with Battery Optimization")
st.markdown(
    """
    **Renewable Energy Forecasting & Battery Arbitrage System**  
    Predicts 24-hour solar generation, evaluates peak-demand Duck Curve dynamics, 
    and optimizes battery storage dispatch via Linear Programming (PuLP).
    """
)

# Sidebar controls
st.sidebar.header("🕹️ Control Panel")
plant_id = st.sidebar.selectbox("Select Solar Power Plant", options=[1, 2], format_func=lambda x: f"Plant {x}")
granularity = st.sidebar.radio("Data Granularity", options=["hourly", "15min_plant"], format_func=lambda x: "Hourly Baseline" if x == "hourly" else "15-Minute Plant Level")

# Load processed data
@st.cache_data
def get_data(pid, freq):
    try:
        return load_processed_handoff(plant_id=pid, freq=freq)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

df = get_data(plant_id, granularity)

if df is not None:
    # High-level KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Total Records", value=f"{len(df):,}")
    with col2:
        max_ac = df["ac_power"].max() if "ac_power" in df.columns else 0
        st.metric(label="Peak AC Power", value=f"{max_ac:.2f} kW")
    with col3:
        avg_ac = df["ac_power"].mean() if "ac_power" in df.columns else 0
        st.metric(label="Average AC Power", value=f"{avg_ac:.2f} kW")
    with col4:
        st.metric(label="Plant ID", value=f"Plant {plant_id}")

    # Tabs for project phases
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Week 1: Generation & Weather EDA",
        "🔮 Week 2: 24h Forecasting Engine",
        "🔋 Week 2-3: Duck Curve & Battery Arbitrage",
        "📋 Week 4: Grid Advisory & Carbon Offsets"
    ])

    with tab1:
        st.subheader("Historical Solar Generation & Solar Irradiance Profile")
        
        # Interactive time series chart with range slider
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["time"],
            y=df["ac_power"],
            mode="lines",
            name="AC Power (kW)",
            line=dict(color="#FF8C00", width=2)
        ))
        
        # If GHI is available, add secondary axis
        if "ghi" in df.columns:
            fig.add_trace(go.Scatter(
                x=df["time"],
                y=df["ghi"],
                mode="lines",
                name="GHI (W/m²)",
                yaxis="y2",
                line=dict(color="#1E90FF", width=1.5, dash="dot")
            ))
            fig.update_layout(
                yaxis2=dict(
                    title="GHI (W/m²)",
                    overlaying="y",
                    side="right",
                    showgrid=False
                )
            )

        fig.update_layout(
            title=f"Plant {plant_id} Generation Profile vs Solar Irradiance",
            xaxis=dict(
                title="Timestamp",
                rangeslider=dict(visible=True),
                type="date"
            ),
            yaxis=dict(title="AC Power (kW)"),
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=50, b=40),
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Processed Handoff Dataset Preview")
        st.dataframe(df.head(50), use_container_width=True)

    with tab2:
        st.subheader("Week 1 AI/ML Baseline Forecasting Benchmark")
        st.markdown(
            """
            Multi-step day-ahead forecasting benchmarks evaluated across a **7-day out-of-sample test horizon (168 hours)** 
            with **strict chronological splitting** and **physical nighttime zero-inflation**.
            """
        )

        pred_file = root_dir / "reports" / f"plant{plant_id}_week1_baseline_predictions.csv"
        metrics_file = root_dir / "reports" / "week1_baseline_metrics_summary.csv"

        if metrics_file.exists():
            summary_df = pd.read_csv(metrics_file)
            plant_metrics = summary_df[summary_df["plant_id"] == plant_id].drop(columns=["plant_id"])
            st.markdown(f"#### 🏆 Model Performance Benchmark — Plant {plant_id}")
            st.dataframe(
                plant_metrics.style.format({
                    "daylight_rmse": "{:.2f} kW",
                    "daylight_mape_pct": "{:.2f}%",
                    "daylight_mae": "{:.2f} kW",
                    "daylight_r2": "{:.4f}",
                    "rmse_overall": "{:.2f} kW",
                    "mae_overall": "{:.2f} kW",
                    "r2_overall": "{:.4f}",
                    "daylight_nrmse_pct": "{:.2f}%"
                }),
                use_container_width=True
            )

        if pred_file.exists():
            df_preds = pd.read_csv(pred_file)
            df_preds["time"] = pd.to_datetime(df_preds["time"])

            st.markdown(f"#### 📈 Out-of-Sample 7-Day Forecast Horizon (Actual vs Baselines)")
            fig_fc = go.Figure()
            fig_fc.add_trace(go.Scatter(
                x=df_preds["time"],
                y=df_preds["actual_ac_power"],
                mode="lines",
                name="Actual Power (kW)",
                line=dict(color="#00FFA3", width=2.5)
            ))
            if "pred_ridge_regression" in df_preds.columns:
                fig_fc.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_ridge_regression"],
                    mode="lines",
                    name="Ridge Regression Baseline",
                    line=dict(color="#FF4B4B", width=2, dash="dash")
                ))
            if "pred_persistence_(24h_lag)" in df_preds.columns:
                fig_fc.add_trace(go.Scatter(
                    x=df_preds["time"],
                    y=df_preds["pred_persistence_(24h_lag)"],
                    mode="lines",
                    name="Persistence (24h Lag)",
                    line=dict(color="#FFA500", width=1.5, dash="dot")
                ))

            fig_fc.update_layout(
                title=f"Plant {plant_id}: 7-Day Out-of-Sample Actual vs. Baseline Predictions",
                xaxis=dict(title="Timestamp", rangeslider=dict(visible=True), type="date"),
                yaxis=dict(title="AC Power (kW)"),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=50, b=40),
                template="plotly_dark"
            )
            st.plotly_chart(fig_fc, use_container_width=True)
        else:
            st.info("Run `python src/models/train_baseline.py` to generate baseline prediction reports.")

    with tab3:
        st.info("Week 2-3 Deliverable: Duck Curve explorer & PuLP Linear Programming battery arbitrage scheduler.")
        st.markdown(
            """
            - **Duck Curve Explorer:** Visualizes the gap between midday solar generation peaks and 6 PM–9 PM peak grid consumer demand.
            - **Battery Optimization:** Schedules charging during low-tariff daylight hours and discharging during high-tariff evening peak hours.
            """
        )

    with tab4:
        st.info("Week 4 Deliverable: Extreme weather scenario testing, carbon offset calculations, and downloadable PDF/Markdown grid briefing.")
else:
    st.warning("Please ensure processed handoff CSVs are available under `data/processed/`.")

# Smart Energy Grid & Solar Power Forecasting with Battery Optimization

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v3.4-38B2AC.svg)](https://tailwindcss.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![PuLP](https://img.shields.io/badge/PuLP-LP%20Optimization-orange.svg)](https://coin-or.github.io/pulp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An end-to-end industrial-grade **Smart Renewable Energy Forecasting & Battery Arbitrage System**. This system forecasts solar power generation at high-frequency 15-minute and hourly resolutions, models grid Duck Curve peak demand dynamics, and utilizes linear programming (PuLP) to schedule battery energy storage dispatch (charging during cheap daylight solar peaks and discharging during expensive evening peak-tariff hours).

Features a **modern enterprise React + Tailwind CSS dashboard** with interactive solar forecasting bounds, radial State-of-Charge (SoC) gauges, Duck Curve load shifting charts, and an automated Time-of-Use (TOU) tariff savings calculator.

---

## Project Overview

Renewable photovoltaic energy exhibits high intraday intermittency due to weather dynamics and diurnal cycles. Power grid operators cannot integrate solar reliably without accurate day-ahead generation forecasts and automated battery storage arbitrage.

This project delivers:
1. **Solar Power Forecasting:** Multi-step day-ahead forecasting using LightGBM and Prophet integrated with pyranometer sensor readings and Open-Meteo numerical weather forecasts (GHI, DNI, DHI, cloud cover, and ambient temperature) with 90% statistical prediction uncertainty bounds.
2. **Duck Curve Analytics:** Quantifying the widening midday net load drop and steep evening ramp demand to evaluate grid stress points.
3. **Battery Storage Arbitrage Optimization:** Linear Programming (LP) optimization formulated via PuLP to maximize revenue subject to battery capacity, C-rate, degradation wear, and depth-of-discharge constraints.
4. **Enterprise React Web Platform & REST API:** High-performance FastAPI backend serving a responsive React + Tailwind CSS web dashboard (with collapsible sidebar and light solar theme), along with the legacy Streamlit explorer.

---

## Repository Structure

```text
Smart-Energy-Grid-and-Solar-Power-Forecasting-with-Battery-Optimization/
│
├── .gitignore                                 # Ignore rules (venv, checkpoints, bytecode, caches)
├── LICENSE                                    # MIT License
├── README.md                                  # Complete project documentation & benchmark report
├── requirements.txt                           # Production dependencies
│
├── run_all.py                                 # Universal cross-platform Python runner
├── run_all.sh                                 # macOS / Linux execution script
├── run_all.bat                                # Windows Command Prompt / PowerShell execution script
│
├── data/                                      # Data directory
│   ├── raw/                                   # Original source datasets
│   │   ├── Plant_1_Generation_Data.csv        # 68,778 raw inverter readings (Plant 1)
│   │   ├── Plant_1_Weather_Sensor_Data.csv    # 3,182 raw sensor readings (Plant 1)
│   │   ├── Plant_2_Generation_Data.csv        # 67,698 raw inverter readings (Plant 2)
│   │   ├── Plant_2_Weather_Sensor_Data.csv    # 3,259 raw sensor readings (Plant 2)
│   │   ├── open-meteo-14.80N78.18E203m.csv   # Supplementary Open-Meteo weather (Plant 1)
│   │   └── open-meteo-14.38N77.50E491m.csv   # Supplementary Open-Meteo weather (Plant 2)
│   │
│   └── processed/                             # Post-EDA handoff datasets
│       ├── AI_ML_TEAM_DATASET_GUIDE.pdf       # Data schema documentation
│       ├── plant1_ai_ml_handoff_15min.csv     # Primary modeling dataset: 68,778 rows (Inverter-level)
│       ├── plant2_ai_ml_handoff_15min.csv     # Primary modeling dataset: 67,698 rows (Inverter-level)
│       ├── plant1_ai_ml_handoff_15min_plantlevel.csv  # 3,158 rows (Whole-plant 15-min aggregate)
│       ├── plant2_ai_ml_handoff_15min_plantlevel.csv  # 3,259 rows (Whole-plant 15-min aggregate)
│       ├── plant1_ai_ml_handoff_hourly.csv    # 816 rows (Whole-plant hourly aggregate)
│       └── plant2_ai_ml_handoff_hourly.csv    # 816 rows (Whole-plant hourly aggregate)
│
├── notebooks/                                 # Exploratory Data Analysis & baseline notebooks
│   ├── PLANT1.ipynb                           # Plant 1 EDA, cleaning & handoff pipeline
│   ├── PLANT2.ipynb                           # Plant 2 EDA, cleaning & handoff pipeline
│   └── 01_week1_ai_ml_baseline.ipynb          # Week 1 AI/ML baseline & feature engineering tutorial
│
├── src/                                       # Production modular codebase
│   ├── __init__.py
│   ├── analysis/                              # Week 4 analytical suites
│   │   ├── __init__.py
│   │   ├── weather_stress_test.py             # 6-scenario extreme-weather stress testing & resilience
│   │   └── carbon_accounting.py               # Operational avoided emissions & CEA v19.0 provenance
│   ├── api/                                   # FastAPI REST backend for web client
│   │   ├── __init__.py
│   │   └── server.py                          # REST endpoints, static frontend mount & PDF delivery
│   ├── data/                                  # Data access & loading
│   │   ├── __init__.py
│   │   └── loader.py                          # Robust path-agnostic data loader
│   ├── features/                              # Feature engineering & preprocessing
│   │   ├── __init__.py
│   │   └── engineering.py                     # Solar geometry, lags, rolling stats, zero-inflation
│   ├── models/                                # Model pipelines, training & evaluation
│   │   ├── __init__.py
│   │   ├── baseline.py                        # Temporal split, persistence & regression baselines
│   │   ├── forecasting.py                     # LightGBM GBDT & Prophet forecasters
│   │   ├── metrics.py                         # Daylight RMSE, Daylight MAPE, nRMSE, R²
│   │   ├── train_baseline.py                  # Week 1 benchmark runner
│   │   └── train_forecasting.py               # Week 2 advanced forecasting & battery runner
│   ├── optimization/                          # Mathematical optimization & dispatch
│   │   ├── __init__.py
│   │   └── battery_lp.py                      # PuLP Linear Programming battery arbitrage
│   └── visualization/                         # Plotting & reporting utilities
│       ├── __init__.py
│       ├── reports_generator.py               # Automated correlation & figure generator
│       └── executive_report.py                # Dynamic multi-page ReportLab PDF executive report
│
├── frontend/                                  # Modern React + Tailwind CSS Web Application
│   ├── index.html                             # Web dashboard HTML entrypoint
│   ├── package.json                           # React 19, Tailwind CSS v3, Recharts, Lucide
│   ├── vite.config.js                         # Vite build configuration with backend proxy
│   ├── tailwind.config.js                     # Solar theme design system
│   ├── public/                                # Public assets (photorealistic solar background)
│   ├── src/                                   # React frontend source
│   │   ├── App.jsx                            # Main application layout & state manager
│   │   └── components/                        # Modular views (Forecast, BESS, Weather, Carbon, Report)
│   └── dist/                                  # Compiled static web distribution (zero-build deploy)
│
├── app/                                       # Streamlit web application (legacy companion)
│   ├── __init__.py
│   └── app.py                                 # Enterprise dashboard entrypoint (with Week 4 tabs)
│
├── reports/                                   # Evaluation outputs & publication figures
│   ├── week1_baseline_metrics_summary.csv     # Week 1 baseline evaluation leaderboard
│   ├── week2_forecasting_metrics_summary.csv  # Week 2 forecasting leaderboard
│   ├── week4_weather_stress_summary.csv       # Week 4 weather stress scenario matrix
│   ├── week4_forecast_stress_metrics.csv      # Week 4 model error spikes under stress
│   ├── week4_battery_resilience.csv           # Week 4 BESS dispatch under climate stress
│   ├── week4_carbon_summary.csv               # Week 4 CEA grid sensitivity summary
│   ├── week4_carbon_scenarios.csv             # Week 4 avoided emissions by weather scenario
│   ├── executive_report_plant1.pdf            # 6-page Executive Technical Report (Plant 1)
│   ├── executive_report_plant2.pdf            # 6-page Executive Technical Report (Plant 2)
│   ├── plant1_week2_forecasting_predictions.csv # 14,740 test horizon predictions (Plant 1)
│   ├── plant2_week2_forecasting_predictions.csv # 14,784 test horizon predictions (Plant 2)
│   ├── plant1_lightgbm_feature_importance.csv # LightGBM feature gain rankings (Plant 1)
│   ├── plant2_lightgbm_feature_importance.csv # LightGBM feature gain rankings (Plant 2)
│   ├── sample_battery_dispatch_plant1.csv     # 24-hour hour-by-hour BESS optimal schedule
│   ├── plant1_correlations.csv                # Correlation matrix (Plant 1)
│   ├── plant2_correlations.csv                # Correlation matrix (Plant 2)
│   └── figures/                               # Exported publication plots (300 DPI)
│
└── tests/                                     # Automated test suites
    ├── __init__.py
    ├── test_data_loader.py                    # Dataset validation and schema integrity tests
    ├── test_week2.py                          # Week 2 forecaster and PuLP LP unit tests
    ├── test_week3.py                          # Week 3 REST API & React frontend tests
    └── test_week4.py                          # Week 4 Stress testing, Carbon & PDF tests
```

---

## Dataset Architecture & Target Specification

### Target Variable: `ac_power` (kW)
- **Target:** **`ac_power`** is the instantaneous usable power delivered by the inverter to the grid or battery system.
- **Why NOT `total_yield`?** `total_yield` is a cumulative lifetime odometer counter that increases monotonically over months/years. It does not measure power output at any given hour. Furthermore, Plant 2 contains hardware reset glitches in `total_yield`. Grid dispatch and battery storage scheduling require forecasting **instantaneous power output (`ac_power`) in kilowatts**.

### Granularity Levels
1. **Inverter-Level 15-Minute (`plant*_ai_ml_handoff_15min.csv` — ~68k Rows):** **Primary modeling dataset**. Contains observations for each of the 22 physical inverters across 34 days ($3,126 \text{ timestamps} \times 22 \text{ inverters} \approx 68,000$ rows).
2. **Plant-Level 15-Minute (`plant*_ai_ml_handoff_15min_plantlevel.csv` — ~3.2k Rows):** Aggregated across all 22 inverters for intra-day whole-plant battery dispatch.
3. **Plant-Level Hourly (`plant*_ai_ml_handoff_hourly.csv` — 816 Rows):** 1-hour resolution for day-ahead market tariff scheduling.

---

## Preprocessing & Feature Engineering Pipeline

Implemented in [`src/features/engineering.py`](src/features/engineering.py) and [`src/models/baseline.py`](src/models/baseline.py):

1. **Astronomical Solar Geometry:**
   - Evaluates solar declination ($\delta$), Equation of Time ($\text{EoT}$), and hour angle ($\omega$) based on plant coordinates (Plant 1: 14.80°N, 78.18°E; Plant 2: 14.38°N, 77.50°E).
   - Generates the **solar elevation angle** ($\alpha$) and **cosine of the solar zenith angle** ($\cos(\theta_z)$).
2. **Autoregressive Lag Features:**
   - Grouped by inverter ID (`source_key`) to eliminate cross-inverter pollution:
     - $t-1\text{step}$ ($15\text{ minutes}$)
     - $t-1\text{h}$ ($4\text{ steps}$)
     - $t-24\text{h}$ ($96\text{ steps}$: same time yesterday for that specific inverter)
3. **Causal Rolling Irradiance Statistics:**
   - 3-hour ($12\text{ steps}$) and 6-hour ($24\text{ steps}$) backward-looking moving averages of GHI and sensor irradiation.
4. **Categorical & Cyclical Encodings:**
   - `inverter_code`: Inverter categorical ID mapped to integers $[0, 21]$.
   - `hour_sin` / `hour_cos`: Continuous circular 24-hour time encoding.
5. **StandardScaler Pipeline:**
   - Standardizes features to zero mean and unit variance. Fitted strictly on training data inside a Scikit-Learn `Pipeline` to prevent test-set data leakage.
6. **Physical Nighttime Zero-Inflation:**
   - Enforces strictly $0.0\text{ kW}$ output when $\alpha \le 0^\circ$ (sun below horizon) or $\text{GHI} \le 1.0\text{ W/m}^2$, eliminating non-physical night predictions.

---

## Week 1 Baseline Benchmark Leaderboard

Evaluated out-of-sample across the final 7 consecutive days (**14,740 test observations** for Plant 1; **14,784 test observations** for Plant 2):

### Solar Power Plant 1 (Inverter-Level 15-Minute Resolution)
| Rank | Model | Daylight RMSE (kW / inv) | Daylight MAPE (%) | Daylight $R^2$ | Overall $R^2$ | Daylight nRMSE (%) |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| 🥇 | **Ridge Regression Baseline** | **125.21** | **22.93%** | **0.8678** | **0.9356** | **8.87%** |
| 🥈 | **Linear Regression Baseline** | 125.29 | 22.91% | 0.8676 | 0.9356 | 8.88% |
| 🥉 | **Diurnal Mean Benchmark** | 192.20 | 36.79% | 0.6885 | 0.8484 | 13.62% |
| 4 | **Persistence (24h Lag)** | 242.15 | 41.18% | 0.5056 | 0.7593 | 17.16% |

### Solar Power Plant 2 (Inverter-Level 15-Minute Resolution)
| Rank | Model | Daylight RMSE (kW / inv) | Daylight MAPE (%) | Daylight $R^2$ | Overall $R^2$ | Daylight nRMSE (%) |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| 🥇 | **Ridge Regression Baseline** | **159.09** | **34.76%** | **0.6964** | **0.8261** | **11.98%** |
| 🥈 | **Linear Regression Baseline** | 159.11 | 34.77% | 0.6963 | 0.8261 | 11.98% |
| 🥉 | **Diurnal Mean Benchmark** | 293.72 | 68.48% | -0.0350 | 0.4074 | 22.11% |
| 4 | **Persistence (24h Lag)** | 302.94 | 62.42% | -0.1011 | 0.3696 | 22.81% |

> **Key finding:** Ridge Regression achieves a **48% lower Daylight RMSE** than the industrial 24h persistence benchmark for Plant 1 and **47% lower** for Plant 2.

---

## Correlation Analysis Highlights

Exported to [`reports/plant1_correlations.csv`](reports/plant1_correlations.csv) and [`reports/plant2_correlations.csv`](reports/plant2_correlations.csv):

- **Strongest Positive Drivers:**
  - Pyranometer Sensor Irradiation ($r = +0.989$ Plant 1, $+0.781$ Plant 2)
  - Module Temperature ($r = +0.955$ Plant 1, $+0.750$ Plant 2)
  - Solar Zenith $\cos(\theta_z)$ ($r = +0.934$ Plant 1, $+0.765$ Plant 2)
  - Global Horizontal Irradiance ($r = +0.912$ Plant 1, $+0.747$ Plant 2)
- **Strongest Negative Drivers:**
  - Relative Humidity ($r = -0.422$ Plant 1, $-0.464$ Plant 2) — high humidity correlates with cloud cover and atmospheric attenuation.
  - Cloud Cover ($r = -0.097$ Plant 1, $-0.070$ Plant 2).

---

## Quickstart & Execution Guide (Windows & Cross-Platform)

### 1. Python Environment Setup
```powershell
# In PowerShell (Windows):
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
*(On macOS / Linux: `python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt`)*

### 2. Frontend Dependencies & Production Build
```powershell
# Navigate to the React frontend directory:
cd frontend
npm install
npm run build     # Compiles production distribution to frontend/dist/
npm run lint      # Runs Oxlint code quality verification (0 errors)
cd ..
```

### 3. Running the Integrated Web Applications

- **Option A: Integrated React + FastAPI Platform (Recommended Week 3 MVP):**
  ```powershell
  # Serves the compiled React production UI and REST API on port 8000:
  python run_all.py --web
  # Alternatively, launch directly via uvicorn:
  python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000
  ```
  Open your browser to: [http://127.0.0.1:8000](http://127.0.0.1:8000)

- **Option B: React Live Development Server (Hot Module Replacement):**
  ```powershell
  # Vite also starts the local FastAPI backend if it is not already running:
  cd frontend
  npm run dev
  ```
  Open the URL printed by Vite, normally [http://127.0.0.1:5173](http://127.0.0.1:5173). No separate backend terminal is needed; Vite restarts the local API if it stops and waits for it before proxying API requests. To use an externally managed API, set `VITE_API_TARGET` before starting Vite.

  The Overview defaults to plant-level 15-minute telemetry. Its capacity factor is calculated for the selected plant as average measured AC power divided by rated plant capacity; mean active power and solar generation also update with the selected plant and time resolution. These are historical telemetry measurements, not live readings.

- **Option C: Streamlit Web Dashboard:**
  ```powershell
  python run_all.py --app
  # Or directly:
  python -m streamlit run app/app.py
  ```
  Open your browser to: [http://localhost:8501](http://localhost:8501)

### 4. Running the Automated Test Suite

- **Single Command Pipeline Check:**
  ```powershell
  python run_all.py --test-only
  ```
- **Run Individual Pytest Suites:**
  ```powershell
  # Run the complete test suite across all 4 weeks (27 passed, 1 skipped):
  pytest tests/ -v

  # Or run individual weekly test suites:
  pytest tests/test_data_loader.py -v  # Week 1 data validation & schema
  pytest tests/test_week2.py -v        # Week 2 LightGBM & PuLP LP optimizer
  pytest tests/test_week3.py -v        # Week 3 REST API & React frontend tests
  pytest tests/test_week4.py -v        # Week 4 Weather Stress, Carbon & PDF tests
  ```

### 5. Programmatic Data Access
```python
from src.data.loader import load_processed_handoff

# Load primary 15-minute inverter dataset (68,778 rows)
df_plant1 = load_processed_handoff(plant_id=1, freq="15min")

# Load hourly aggregated plant handoff (816 rows)
df_hourly = load_processed_handoff(plant_id=1, freq="hourly")
```

---

## Technical Specifications, Units & Assumptions

### Target Variable & Power vs. Energy Units
- **Target Variable:** Instantaneous AC Power (`ac_power`) in kilowatts (kW) and megawatts (MW).
- **Cumulative Total Yield:** `total_yield` is a lifetime odometer reading with hardware resets and is strictly excluded from instantaneous power forecasting and dispatch equations.
- **Energy Integration:** Power readings are integrated across time-step duration $\Delta t$ ($\Delta t = 0.25\text{ h}$ for 15-minute data; $\Delta t = 1.0\text{ h}$ for hourly data):
  $$E (\text{kWh}) = P (\text{kW}) \times \Delta t (\text{h}), \quad E (\text{MWh}) = \frac{E (\text{kWh})}{1000}$$

### Simulated Grid Demand Transparency Notice
- **Actual Utility Telemetry:** Actual regional grid demand measurements are unavailable for these solar plants.
- **Calibrated Synthetic Scenario:** The grid demand curve used in the Duck Curve explorer and battery arbitrage dispatch is a calibrated diurnal simulation scaled to plant capacity. It is explicitly labeled across all dashboards and API responses as a `Simulated Grid Demand Scenario`. Net load is calculated strictly as $\text{Net Load} = \text{Demand} - \text{Solar Generation}$.

### Currency & Tariff Assumptions
- **Currency:** Battery optimization, weather scenarios, dashboards, charts, API results, and executive PDFs use Indian Rupees (₹ / INR).
- **Central tariff assumptions:** `src/optimization/tariff_config.py` defines the default simulated rates: off-peak ₹5.30/kWh (22:00–06:00), normal ₹6.70/kWh (10:00–18:00), peak ₹7.30/kWh (06:00–10:00 and 18:00–22:00), and zero export credit. The React dashboard reads these settings from `/api/tariff-config`; Streamlit and report generation use the same Python configuration.
- **Other financial assumptions:** Battery degradation wear is estimated at ₹0.50/kWh throughput and illustrative installed cost at ₹15,000/kWh.
- **Estimated savings disclaimer:** All financial results are estimates based on simulated tariff assumptions, not actual plant billing records, utility bills, or guaranteed savings. Users may adjust rates in the dashboards.
- **Annualized savings:** Annual savings are scenario-based projections calculated as estimated daily net savings × 365; they represent a 365-day cycling extrapolation rather than audited 12-month utility bill records.
- **Negative Arbitrage Handling:** When battery degradation wear and round-trip efficiency losses exceed the tariff spread, the LP optimizer stays idle or reports negative arbitrage rather than forcing artificial positive savings.

### Known Environment Constraints
- **Prophet Stan Binary (Windows Python 3.13):** On Windows Python 3.13, CmdStan may report an illegal system DLL relocation (`WinError 623`) when spawning the subprocess binary. LightGBM (GBDT) and Ridge Regression operate without external C++ binary runtime dependencies and serve as the verified primary forecasting models.

---

## Week 2 Advanced Forecasting & PuLP Battery Optimization Leaderboard

Evaluated out-of-sample across the 7-day test horizon (14,740 test samples for Plant 1; 14,784 for Plant 2):

### Solar Power Plant 1 Leaderboard
| Rank | Model | Architecture | Daylight RMSE (kW / inv) | Daylight MAPE (%) | Daylight $R^2$ | Overall $R^2$ | Daylight nRMSE (%) |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|
| 🥇 | **Ridge Regression Baseline** | Regularized L2 Linear | **125.21** | **22.93%** | **0.8678** | **0.9356** | **8.87%** |
| 🥈 | **LightGBM Forecaster** | Gradient Boosted Trees | 152.31 | 25.77% | 0.8044 | 0.9048 | 10.79% |
| 🥉 | **Prophet Forecaster** | Additive Seasonality + Regressors | 183.42 | 47.54% | 0.7163 | 0.8619 | 13.00% |
| 4 | **Persistence Benchmark** | 24h Lagged Ground Truth | 242.15 | 41.18% | 0.5056 | 0.7593 | 17.16% |

### Solar Power Plant 2 Leaderboard
| Rank | Model | Architecture | Daylight RMSE (kW / inv) | Daylight MAPE (%) | Daylight $R^2$ | Overall $R^2$ | Daylight nRMSE (%) |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|
| 🥇 | **Ridge Regression Baseline** | Regularized L2 Linear | **159.09** | **34.76%** | **0.6964** | **0.8261** | **11.98%** |
| 🥈 | **LightGBM Forecaster** | Gradient Boosted Trees | 163.44 | 34.11% | 0.6795 | 0.8165 | 12.30% |
| 🥉 | **Prophet Forecaster** | Additive Seasonality + Regressors | 225.24 | 55.39% | 0.3913 | 0.6515 | 16.96% |
| 4 | **Persistence Benchmark** | 24h Lagged Ground Truth | 302.94 | 62.42% | -0.1011 | 0.3696 | 22.81% |

---

## PuLP Battery Energy Storage System (BESS) Linear Programming

Implemented in [`src/optimization/battery_lp.py`](src/optimization/battery_lp.py):

- **Objective:** Minimize daily electricity import costs minus export feed-in revenues subject to battery throughput wear:
  $$\min \sum_{t=1}^{T} \left( C_{\text{import}, t} \cdot P_{\text{import}, t} \cdot \Delta t - C_{\text{export}, t} \cdot P_{\text{export}, t} \cdot \Delta t + C_{\text{deg}} \cdot (P_{\text{ch}, t} + P_{\text{dis}, t}) \cdot \Delta t \right)$$
- **Physical Constraints:**
  1. **Power Balance:** $P_{\text{solar}, t} + P_{\text{dis}, t} + P_{\text{import}, t} = P_{\text{load}, t} + P_{\text{ch}, t} + P_{\text{export}, t}$
  2. **SoC Dynamics:** $E_t = E_{t-1} + \left( \eta_{\text{ch}} P_{\text{ch}, t} - \frac{1}{\eta_{\text{dis}}} P_{\text{dis}, t} \right) \Delta t$
  3. **Capacity & Operational Bounds:** $\text{SoC}_{\min} \cdot E_{\text{cap}} \le E_t \le \text{SoC}_{\max} \cdot E_{\text{cap}}$ and $0 \le P_{\text{ch}, t} \le P_{\text{ch}}^{\max}$, $0 \le P_{\text{dis}, t} \le P_{\text{dis}}^{\max}$
  4. **Terminal SoC:** $E_T \ge E_0$ (ensures zero depletion free-riding across days)

**24-Hour Benchmark Result (Plant 1 - 10 MWh / 5 MW BESS):**
- **Estimated unmanaged electricity cost:** ₹518,759.10
- **Estimated optimized electricity cost (with BESS):** ₹469,653.05
- **Estimated savings:** **₹49,106.05 (9.47% cost reduction)**
- **Solar self-consumption:** Increased from **48.95%** to **55.17%**
- These results use the simulated INR tariffs above; they are estimates, not actual bills or guaranteed savings.

---

## Week 4 Deliverables: Weather Stress Testing, Carbon Accounting & Executive Reports

### 1. Extreme-Weather Stress Testing Module
Implemented in [`src/analysis/weather_stress_test.py`](src/analysis/weather_stress_test.py):
Evaluates model forecast error degradation and PuLP battery storage resilience across six calibrated meteorological anomaly scenarios:
1. **Normal Baseline:** Measured baseline weather and solar generation.
2. **Heavy Cloud Cover:** 50% solar irradiance reduction throughout the test period.
3. **Monsoon Prolonged Low-Irradiance:** 75% solar irradiance reduction and a 4°C temperature decrease.
4. **Sudden Midday Irradiance Drop:** One 75% drop from 11:00 to 14:00 on the first test day.
5. **Multi-Day Continuous Solar Deficit:** 60% solar irradiance reduction over the first 72 hours.
6. **Post-Storm Rapid Recovery:** 80% reduction through 11:00 on the first test day, then normal irradiance.

**Physical Validation:** Strictly enforces astronomical night zero-inflation (when solar elevation $\le 0^\circ$ or GHI $\le 1.0\text{ W/m}^2$, output is clamped to $0.0\text{ kW}$).

**Weather Dashboard Metric Definitions:** Solar generation, peak power, and Ridge/LightGBM daylight RMSE use the same seven-day test interval. The RMSE daylight mask is fixed from measured baseline output above 10 kW and reused for all scenarios; RMSE is in kW. The normal case uses measured telemetry; other weather cases are synthetic. Battery metrics are 24-hour optimization estimates using the fixed modeled-demand profile described above. Grid dependence is grid imports divided by modeled facility demand; autonomy is 100% minus grid dependence.

### 2. Operational Carbon-Offset Accounting & CEA Provenance
Implemented in [`src/analysis/carbon_accounting.py`](src/analysis/carbon_accounting.py):
- **Official Regulatory Provenance:** Baseline emission factors derived directly from the official **Central Electricity Authority (CEA), Ministry of Power, Government of India** *CO2 Baseline Database for the Indian Power Sector, User Guide Version 19.0 (Published Dec 2024)*.
- **Emission Factors:**
  - National Weighted Average Baseline: **0.716 kg CO₂e / kWh**
  - Thermal Marginal Fossil Peaker: **0.820 kg CO₂e / kWh**
  - Clean Low-Carbon Grid Sensitivity: **0.500 kg CO₂e / kWh**
  - High-Coal Subcritical Grid Sensitivity: **0.950 kg CO₂e / kWh**
- **Boundary Condition:** Reflects operational marginal grid electricity displacement at the high-voltage transmission interface. Discloses that cradle-to-grave photovoltaic module and battery manufacturing life-cycle assessment (LCA) is excluded.
- **Formulas:**
  $$\text{Displaced Grid Electricity (kWh)} = \max(0, \text{Import}_{\text{without BESS}} - \text{Import}_{\text{with BESS}})$$
  $$\text{Avoided CO}_2 (\text{kg}) = \left(\text{Displaced Grid kWh} + \text{Solar Self-Consumed kWh}\right) \times \text{EF}_{\text{grid}}$$

### 3. Dynamic Executive Technical PDF Report Engine
Implemented in [`src/visualization/executive_report.py`](src/visualization/executive_report.py):
Generates a publication-grade, 6-page comprehensive executive PDF report via ReportLab 5.1.0:
- **Page 1:** Executive Summary, 6 KPI cards, and mandatory regulatory disclaimers (CEA v19.0, synthetic demand, benchmark tariffs).
- **Page 2:** Solar Resource & Plant Generation Dynamics (diurnal generation curves, temperature derating correlations).
- **Page 3:** Solar Forecasting & Calibrated Uncertainty Bounds (Ridge vs LightGBM vs Prophet, $\pm 1.28\sigma$ and $\pm 1.96\sigma$ intervals).
- **Page 4:** Substation Duck Curve & Grid Ramp Dynamics (15-min simulated load vs solar influx, net load belly, evening ramp rate $+1.53\text{ MW/h}$).
- **Page 5:** PuLP Battery Storage Optimization (2.0 MWh / 0.5 MW BESS dispatch, state-of-charge envelope [10%-90%], degradation wear cost deduction).
- **Page 6:** Extreme-Weather Stress Testing & Carbon Accounting (6-scenario stress matrix, CEA sensitivity table, and engineering roadmap).
- **Canvas Architecture:** Two-pass `NumberedCanvas` computing dynamic running headers, footers, and exact page counts ("Page X of Y").

### 4. REST API Endpoints (FastAPI)
| Method | Endpoint | Description |
|:---:|---|---|
| `GET` | `/api/status` | System health check, active models, and pipeline status |
| `GET` | `/api/plants` | Facility metadata (Gandikota Plant 1 & Ananthapuramu Plant 2) |
| `GET` | `/api/overview` | Plant telemetry, diurnal KPIs, and rolling timeseries |
| `GET` | `/api/forecast` | 24-hour day-ahead predictions with statistical bounds |
| `GET` | `/api/duck-curve` | 15-minute simulated demand, solar generation, and net load |
| `POST` | `/api/optimize` | PuLP LP battery dispatch optimization and tariff savings |
| `GET` | `/api/weather-stress` | 6 extreme-weather stress scenarios, forecast errors, and BESS resilience |
| `GET` | `/api/carbon` | CEA v19.0 carbon accounting, sensitivity matrix, and custom factor calculator |
| `POST` | `/api/executive-report/generate` | Compiles dynamic 6-page executive PDF report via ReportLab |
| `GET` | `/api/executive-report/download` | Streams generated executive PDF report to browser |

---

## 4-Week Milestone Roadmap

- [x] **Week 1:** Data cleaning, inverter coverage validation, weather EDA, time-based split, feature engineering, physical zero-inflation, baseline regression benchmarking, correlation matrices, and analytical figure generation.
- [x] **Week 2:** Advanced 24-hour multi-step forecasting with LightGBM and Prophet, Time-of-Use (TOU) tariff matrix, PuLP Linear Programming battery arbitrage formulation, and Duck Curve net grid load explorer.
- [x] **Week 3:** Enterprise React + Tailwind CSS dashboard & Streamlit app with statistical forecast bounds, radial battery State-of-Charge (SoC) gauges, automated charge/discharge schedules, and net tariff savings calculator; MVP frozen.
- [x] **Week 4:** Extreme-weather stress-testing (6 scenarios), operational carbon offset accounting (CEA v19.0 provenance), dynamic 6-page ReportLab executive PDF reports, full REST API integration, and comprehensive test suite across all weeks.

---

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

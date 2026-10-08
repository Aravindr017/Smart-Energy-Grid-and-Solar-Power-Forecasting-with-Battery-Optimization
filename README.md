# Smart Energy Grid & Solar Power Forecasting with Battery Optimization

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B.svg)](https://streamlit.io/)

An end-to-end industrial-grade **Smart Renewable Energy Forecasting & Battery Arbitrage System**. This system forecasts solar power generation at high-frequency 15-minute and hourly resolutions, models grid Duck Curve peak demand dynamics, and utilizes linear programming (PuLP) to schedule battery energy storage dispatch (charging during cheap daylight solar peaks and discharging during expensive evening peak-tariff hours).

---

## Project Overview

Renewable photovoltaic energy exhibits high intraday intermittency due to weather dynamics and diurnal cycles. Power grid operators cannot integrate solar reliably without accurate day-ahead generation forecasts and automated battery storage arbitrage.

This project delivers:
1. **Solar Power Forecasting:** Multi-step day-ahead forecasting using machine learning integrated with pyranometer sensor readings and Open-Meteo numerical weather forecasts (GHI, DNI, DHI, cloud cover, and ambient temperature).
2. **Duck Curve Analytics:** Quantifying the widening midday net load drop and steep evening ramp demand to evaluate grid stress points.
3. **Battery Storage Arbitrage Optimization:** Linear Programming (LP) optimization formulated via PuLP to maximize revenue subject to battery capacity, C-rate, and depth-of-discharge constraints.
4. **Interactive Enterprise Dashboard:** Streamlit application providing generation analysis, out-of-sample forecast benchmarking, diurnal profiling, and dataset inspection.

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
│   ├── data/                                  # Data access & loading
│   │   ├── __init__.py
│   │   └── loader.py                          # Robust path-agnostic data loader
│   ├── features/                              # Feature engineering & preprocessing
│   │   ├── __init__.py
│   │   └── engineering.py                     # Solar geometry, lags, rolling stats, zero-inflation
│   ├── models/                                # Model pipelines, training & evaluation
│   │   ├── __init__.py
│   │   ├── baseline.py                        # Temporal split, persistence & regression baselines
│   │   ├── metrics.py                         # Daylight RMSE, Daylight MAPE, nRMSE, R²
│   │   └── train_baseline.py                  # Benchmark runner for Plant 1 and Plant 2
│   └── visualization/                         # Plotting & reporting utilities
│       ├── __init__.py
│       └── reports_generator.py               # Automated correlation & figure generator
│
├── app/                                       # Streamlit web application
│   ├── __init__.py
│   └── app.py                                 # Enterprise dashboard entrypoint
│
├── reports/                                   # Evaluation outputs & publication figures
│   ├── week1_baseline_metrics_summary.csv     # Model evaluation leaderboard
│   ├── plant1_week1_baseline_predictions.csv  # 14,740 test horizon predictions (Plant 1)
│   ├── plant2_week1_baseline_predictions.csv  # 14,784 test horizon predictions (Plant 2)
│   ├── plant1_correlations.csv                # Correlation matrix (Plant 1)
│   ├── plant2_correlations.csv                # Correlation matrix (Plant 2)
│   └── figures/                               # Exported publication plots (300 DPI)
│       ├── plant1_correlation_heatmap.png
│       ├── plant2_correlation_heatmap.png
│       ├── plant1_weather_irradiance_scatter.png
│       ├── plant2_weather_irradiance_scatter.png
│       ├── plant1_diurnal_generation_profile.png
│       ├── plant2_diurnal_generation_profile.png
│       ├── plant1_actual_vs_predicted_7days.png
│       ├── plant2_actual_vs_predicted_7days.png
│       ├── plant1_residuals_distribution.png
│       └── plant2_residuals_distribution.png
│
└── tests/                                     # Automated test suites
    ├── __init__.py
    └── test_data_loader.py                    # Dataset validation and schema integrity tests
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

## Quickstart & Execution

### 1. Environment Setup
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Single-Command Pipeline Execution (Cross-Platform)

- **macOS / Linux:**
  ```bash
  ./run_all.sh              # Runs data checks, model training & figure exports
  ./run_all.sh --app        # With Streamlit dashboard
  ```

- **Windows:**
  ```cmd
  run_all.bat               # In Command Prompt / PowerShell
  run_all.bat --app         # With Streamlit dashboard
  ```

- **Universal Python:**
  ```bash
  python run_all.py         # Standard pipeline run
  python run_all.py --app   # Launch dashboard
  ```

### 3. Programmatic Data Access
```python
from src.data.loader import load_processed_handoff

# Load primary 15-minute inverter dataset (68,778 rows)
df_plant1 = load_processed_handoff(plant_id=1, freq="15min")

# Load hourly aggregated plant handoff (816 rows)
df_hourly = load_processed_handoff(plant_id=1, freq="hourly")
```

---

## 4-Week Milestone Roadmap

- [x] **Week 1:** Data cleaning, inverter coverage validation, weather EDA, time-based split, feature engineering, physical zero-inflation, baseline regression benchmarking, correlation matrices, and analytical figure generation.
- [ ] **Week 2:** Duck Curve net grid load explorer, Time-of-Use (TOU) tariff matrix, 24-hour multi-step forecasting with LightGBM, XGBoost, and Prophet, and PuLP Linear Programming battery arbitrage formulation.
- [ ] **Week 3:** Streamlit application integration with forecast bounds, battery State-of-Charge (SoC) gauges, automated charge/discharge schedules, and net tariff savings calculator.
- [ ] **Week 4:** Monsoon and cloud cover stress-testing, carbon offset calculations (kg CO₂ avoided), and downloadable executive grid advisory reports.

---

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

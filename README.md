# Smart Energy Grid & Solar Power Forecasting with Battery Optimization

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B.svg)](https://streamlit.io/)

An end-to-end Smart Renewable Energy Forecasting & Battery Arbitrage System. This project predicts 24-hour solar generation from weather sensors and meteorological forecasts, analyzes grid peak-demand Duck Curve patterns, and uses linear programming (PuLP) to optimize battery storage dispatch for maximum economic arbitrage and carbon reduction.

---

## ⚡ Project Overview

Renewable solar energy is inherently variable due to passing clouds, rain, and diurnal/seasonal patterns. Power grid operators cannot rely on photovoltaic generation without accurate day-ahead forecasts and intelligent storage systems.

This system bridges the gap by:
1. **Solar Power Forecasting:** Multi-step 24-hour hourly generation forecasting using machine learning (LightGBM, XGBoost, and Prophet) integrated with physical sensor readings and Open-Meteo solar radiation forecasts (GHI, DNI, DHI, cloud cover).
2. **Duck Curve Analysis:** Visualizing the widening midday drop in net load and evening ramp-up demand to identify grid stress points.
3. **Battery Storage Arbitrage Optimization:** Formulating a Linear Programming (LP) optimization problem using PuLP to schedule battery charging during low-tariff daylight solar peaks and discharging during high-tariff evening peak hours.
4. **Interactive Executive Dashboard:** A Streamlit dashboard with real-time forecast tracking, interactive battery State-of-Charge (SoC) gauges, tariff savings calculators, and grid advisory reports.

---

## 📁 Repository Structure

```text
Smart-Energy-Grid-and-Solar-Power-Forecasting-with-Battery-Optimization/
│
├── .gitignore                         # GitHub ignore rules (venv, checkpoints, bytecode, caches)
├── LICENSE                            # MIT License
├── README.md                          # Comprehensive project documentation
├── requirements.txt                   # Complete project dependencies
│
├── data/                              # Data directory
│   ├── raw/                           # Original datasets
│   │   ├── Plant_1_Generation_Data.csv
│   │   ├── Plant_1_Weather_Sensor_Data.csv
│   │   ├── Plant_2_Generation_Data.csv
│   │   ├── Plant_2_Weather_Sensor_Data.csv
│   │   ├── open-meteo-14.80N78.18E203m.csv   # Plant 1 supplementary weather
│   │   └── open-meteo-14.38N77.50E491m.csv   # Plant 2 supplementary weather
│   └── processed/                     # Post-EDA & merged handoff datasets
│       ├── AI_ML_TEAM_DATASET_GUIDE.pdf
│       ├── plant1_ai_ml_handoff_hourly.csv
│       ├── plant1_ai_ml_handoff_15min_plantlevel.csv
│       ├── plant1_ai_ml_handoff_15min.csv
│       ├── plant2_ai_ml_handoff_hourly.csv
│       ├── plant2_ai_ml_handoff_15min_plantlevel.csv
│       └── plant2_ai_ml_handoff_15min.csv
│
├── notebooks/                         # Exploratory Data Analysis & experiments
│   ├── PLANT1.ipynb                   # Plant 1 EDA, cleaning & handoff pipeline
│   └── PLANT2.ipynb                   # Plant 2 EDA, cleaning & handoff pipeline
│
├── src/                               # Production source code
│   ├── __init__.py
│   ├── data/                          # Data loading & Open-Meteo fetching
│   │   ├── __init__.py
│   │   └── loader.py                  # Robust raw/processed dataset loaders
│   ├── features/                      # Time-series feature engineering
│   │   └── __init__.py                # Lags, rolling irradiance, solar zenith angle
│   ├── models/                        # 24h forecasting models & metrics
│   │   └── __init__.py                # Baseline, LightGBM, XGBoost, Prophet, RMSE/MAPE
│   ├── optimization/                  # Linear programming battery scheduler
│   │   └── __init__.py                # PuLP battery arbitrage model
│   └── visualization/                 # Plotting & charts
│       └── __init__.py                # Duck curve, generation curves, SoC timeline
│
├── app/                               # Streamlit web application
│   ├── __init__.py
│   ├── app.py                         # Main Streamlit dashboard
│   └── components/                    # Modular UI components & metrics
│       └── __init__.py
│
├── reports/                           # Output summaries, grid briefs & advisory reports
│   └── .gitkeep
│
└── tests/                             # Unit tests & pipeline validation
    ├── __init__.py
    └── test_data_loader.py
```

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Core & Scientific** | Python 3.10+, Pandas, NumPy, SciPy |
| **Data Visualization** | Plotly, Matplotlib, Seaborn |
| **Machine Learning** | Scikit-Learn, LightGBM, XGBoost, Prophet |
| **Mathematical Optimization** | PuLP (Linear Programming) |
| **Web Dashboard** | Streamlit |
| **APIs & Data Source** | Kaggle Solar Power Dataset, Open-Meteo Solar Radiation API |

---

## 🗓️ 4-Week Milestone Roadmap

### **Week 1: Data Cleaning, EDA & Baseline Models**
- **Data Science:** Clean solar plant and inverter logs; aggregate plant-level 15-minute and hourly generation; inspect temperature coefficients and inverter clipping; integrate Open-Meteo supplementary data.
- **AI/ML:** Temporal train/test split, time-series feature engineering (solar zenith estimates, rolling irradiation, lags), zero-inflation handling for night hours, baseline regression models.

### **Week 2: Duck Curve, Forecasting & LP Formulation**
- **Data Science:** Model grid load curves to visualize the Duck Curve phenomenon; construct Time-of-Use (TOU) tariff matrix and economic savings models.
- **AI/ML:** Train and benchmark multi-step 24-hour forecast models (LightGBM vs XGBoost vs Prophet); formulate battery optimization in PuLP (capacity, C-rate, depth-of-discharge constraints).

### **Week 3: Interactive Dashboard MVP**
- **Joint MVP:** Build the Streamlit application integrating 24h solar forecast line charts, dynamic battery charge/discharge schedule timelines, State-of-Charge (SoC) gauges, and TOU tariff savings calculators.

### **Week 4: Scenario Stress-Testing & Final Delivery**
- **Validation & Refinement:** Test extreme weather scenarios (monsoon, persistent overcast, sudden cloud drops); compute carbon offset metrics (kg CO₂ avoided); generate downloadable Daily Grid Advisory Reports; finalize documentation and presentation.

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/Aravindr017/Smart-Energy-Grid-and-Solar-Power-Forecasting-with-Battery-Optimization.git
cd Smart-Energy-Grid-and-Solar-Power-Forecasting-with-Battery-Optimization
```

### 2. Set Up Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Everything with One Command (Cross-Platform)

We provide one-click runners for both Windows and macOS/Linux:

- **Any Platform (Python):**
  ```bash
  python run_all.py         # Runs validation tests + baseline training
  python run_all.py --app   # Runs pipeline AND launches the Streamlit app
  ```

- **macOS / Linux:**
  ```bash
  ./run_all.sh              # Double-click or run from terminal
  ./run_all.sh --app        # With Streamlit dashboard
  ```

- **Windows:**
  ```cmd
  run_all.bat               # Double-click in Explorer or run from Command Prompt
  run_all.bat --app         # With Streamlit dashboard
  ```

### 5. Running the Notebooks
The notebooks in `notebooks/` are configured to automatically resolve datasets in `data/raw/` and output to `data/processed/` whether executed locally in VS Code / Antigravity IDE or in Google Colab:
```bash
jupyter notebook notebooks/01_week1_ai_ml_baseline.ipynb
```

### 5. Accessing Data Programmatically
Use the centralized data loader in `src/data/loader.py`:
```python
from src.data.loader import load_processed_handoff, load_raw_generation

# Load post-EDA hourly handoff for Plant 1
df_plant1 = load_processed_handoff(plant_id=1, freq="hourly")

# Load raw generation records
df_raw = load_raw_generation(plant_id=1)
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

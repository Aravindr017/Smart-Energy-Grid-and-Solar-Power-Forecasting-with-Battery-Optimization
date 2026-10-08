"""
Data Loader Module
Provides centralized, path-agnostic data loading for raw and processed datasets
across Plant 1 and Plant 2.
"""

from pathlib import Path
from typing import Optional, Union
import pandas as pd


def get_project_root() -> Path:
    """
    Locates the project root directory by searching upward from the current file
    or working directory for recognizable markers (.git, requirements.txt, or data folder).
    """
    # Try relative to this file
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "requirements.txt").exists() or (current / "data").exists() or (current / ".git").exists():
            return current
        current = current.parent

    # Fallback to current working directory
    cwd = Path.cwd()
    for _ in range(5):
        if (cwd / "requirements.txt").exists() or (cwd / "data").exists() or (cwd / ".git").exists():
            return cwd
        cwd = cwd.parent

    return Path.cwd()


def get_data_dirs() -> tuple[Path, Path]:
    """Returns (raw_dir, processed_dir) paths resolved against the project root."""
    root = get_project_root()
    raw_dir = root / "data" / "raw"
    processed_dir = root / "data" / "processed"
    return raw_dir, processed_dir


def load_raw_generation(plant_id: int = 1) -> pd.DataFrame:
    """Loads raw inverter generation data for Plant 1 or Plant 2."""
    raw_dir, _ = get_data_dirs()
    filename = f"Plant_{plant_id}_Generation_Data.csv"
    filepath = raw_dir / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Raw generation file not found: {filepath}")
    return pd.read_csv(filepath)


def load_raw_weather(plant_id: int = 1) -> pd.DataFrame:
    """Loads raw weather sensor data for Plant 1 or Plant 2."""
    raw_dir, _ = get_data_dirs()
    filename = f"Plant_{plant_id}_Weather_Sensor_Data.csv"
    filepath = raw_dir / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Raw weather sensor file not found: {filepath}")
    return pd.read_csv(filepath)


def load_raw_openmeteo(plant_id: int = 1) -> pd.DataFrame:
    """
    Loads supplementary Open-Meteo irradiance & weather data.
    Plant 1 -> 14.80N, 78.18E (203m)
    Plant 2 -> 14.38N, 77.50E (491m)
    """
    raw_dir, _ = get_data_dirs()
    if plant_id == 1:
        filename = "open-meteo-14.80N78.18E203m.csv"
    elif plant_id == 2:
        filename = "open-meteo-14.38N77.50E491m.csv"
    else:
        raise ValueError(f"Invalid plant_id: {plant_id}. Expected 1 or 2.")
    
    filepath = raw_dir / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Open-Meteo file not found: {filepath}")
    return pd.read_csv(filepath, skiprows=3)


def load_processed_handoff(plant_id: int = 1, freq: str = "hourly") -> pd.DataFrame:
    """
    Loads post-EDA AI/ML handoff datasets.
    
    Args:
        plant_id: 1 or 2
        freq: 'hourly', '15min_plant', or '15min_inverter'
    """
    _, processed_dir = get_data_dirs()
    
    mapping = {
        "hourly": f"plant{plant_id}_ai_ml_handoff_hourly.csv",
        "15min_plant": f"plant{plant_id}_ai_ml_handoff_15min_plantlevel.csv",
        "15min_inverter": f"plant{plant_id}_ai_ml_handoff_15min.csv",
    }
    
    if freq not in mapping:
        raise ValueError(f"Unsupported frequency: {freq}. Choose from {list(mapping.keys())}")
        
    filepath = processed_dir / mapping[freq]
    if not filepath.exists():
        raise FileNotFoundError(f"Processed handoff file not found: {filepath}")
        
    df = pd.read_csv(filepath)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])
    return df

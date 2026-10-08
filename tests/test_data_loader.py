"""
Tests for Data Loader and Dataset Integrity
"""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

from src.data.loader import (
    get_project_root,
    get_data_dirs,
    load_raw_generation,
    load_raw_weather,
    load_raw_openmeteo,
    load_processed_handoff,
)


def test_project_root_and_data_dirs():
    root = get_project_root()
    raw_dir, processed_dir = get_data_dirs()
    assert root.exists(), "Root directory must exist"
    assert raw_dir.exists(), "Raw data directory must exist"
    assert processed_dir.exists(), "Processed data directory must exist"
    print("✔ Root and data directories verified.")


def test_raw_files_exist_and_load():
    for pid in [1, 2]:
        df_gen = load_raw_generation(plant_id=pid)
        assert not df_gen.empty, f"Plant {pid} raw generation is empty"
        assert "DATE_TIME" in df_gen.columns, f"DATE_TIME missing in Plant {pid} generation"
        assert "AC_POWER" in df_gen.columns, f"AC_POWER missing in Plant {pid} generation"

        df_weather = load_raw_weather(plant_id=pid)
        assert not df_weather.empty, f"Plant {pid} raw weather is empty"
        assert "DATE_TIME" in df_weather.columns, f"DATE_TIME missing in Plant {pid} weather"

        df_om = load_raw_openmeteo(plant_id=pid)
        assert not df_om.empty, f"Plant {pid} Open-Meteo data is empty"
    print("✔ Raw generation, weather, and Open-Meteo datasets loaded successfully.")


def test_processed_handoff_files_load():
    for pid in [1, 2]:
        df_hourly = load_processed_handoff(plant_id=pid, freq="hourly")
        assert not df_hourly.empty, f"Plant {pid} hourly handoff is empty"
        assert "time" in df_hourly.columns, f"'time' column missing in Plant {pid} hourly handoff"
        assert len(df_hourly) == 816, f"Expected 816 rows, got {len(df_hourly)}"

        df_plant_15m = load_processed_handoff(plant_id=pid, freq="15min_plant")
        assert not df_plant_15m.empty, f"Plant {pid} 15min plant handoff is empty"

        df_inv_15m = load_processed_handoff(plant_id=pid, freq="15min_inverter")
        assert not df_inv_15m.empty, f"Plant {pid} 15min inverter handoff is empty"
    print("✔ All processed handoff datasets (hourly, 15min-plant, 15min-inverter) loaded successfully.")


if __name__ == "__main__":
    print("Testing Data Loader & Dataset Integrity...")
    test_project_root_and_data_dirs()
    test_raw_files_exist_and_load()
    test_processed_handoff_files_load()
    print("All tests passed with zero errors!")

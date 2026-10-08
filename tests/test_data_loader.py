"""
Tests for Data Loader and Dataset Integrity
"""

import pytest
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
    assert root.exists()
    assert raw_dir.exists()
    assert processed_dir.exists()


def test_raw_files_exist_and_load():
    df_gen1 = load_raw_generation(plant_id=1)
    assert not df_gen1.empty
    assert "DATE_TIME" in df_gen1.columns
    assert "AC_POWER" in df_gen1.columns

    df_weather1 = load_raw_weather(plant_id=1)
    assert not df_weather1.empty
    assert "DATE_TIME" in df_weather1.columns

    df_om1 = load_raw_openmeteo(plant_id=1)
    assert not df_om1.empty


def test_processed_handoff_files_load():
    df_hourly1 = load_processed_handoff(plant_id=1, freq="hourly")
    assert not df_hourly1.empty
    assert "time" in df_hourly1.columns
    assert len(df_hourly1) == 816

    df_hourly2 = load_processed_handoff(plant_id=2, freq="hourly")
    assert not df_hourly2.empty
    assert "time" in df_hourly2.columns
    assert len(df_hourly2) == 816

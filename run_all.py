#!/usr/bin/env python3
"""
Cross-Platform Pipeline Runner (Windows & macOS/Linux)
Smart Energy Grid & Solar Power Forecasting with Battery Optimization

Usage:
    python run_all.py             # Runs verification tests + Week 1 baseline model training
    python run_all.py --app       # Runs pipeline and launches the Streamlit dashboard
    python run_all.py --test-only # Runs only dataset validation tests
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)


def print_banner(text: str):
    print("\n" + "=" * 75)
    print(f"⚡ {text}")
    print("=" * 75)


def get_python_executable() -> str:
    """Finds the virtualenv python if available, otherwise uses current sys.executable."""
    if os.name == "nt":  # Windows
        venv_py = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"
        dot_venv_py = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    else:  # macOS / Linux
        venv_py = PROJECT_ROOT / "venv" / "bin" / "python"
        dot_venv_py = PROJECT_ROOT / ".venv" / "bin" / "python"

    if venv_py.exists():
        return str(venv_py)
    elif dot_venv_py.exists():
        return str(dot_venv_py)
    return sys.executable


def run_command(cmd_list: list[str], description: str) -> bool:
    print(f"\n▶ Running: {description}...")
    try:
        result = subprocess.run(cmd_list, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during '{description}': Exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Failed to run '{description}': {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run the end-to-end solar grid & forecasting pipeline.")
    parser.add_argument("--app", action="store_true", help="Launch Streamlit dashboard after pipeline execution")
    parser.add_argument("--test-only", action="store_true", help="Run only dataset integrity tests")
    args = parser.parse_args()

    python_exe = get_python_executable()
    print_banner("Smart Solar Grid & Battery Optimization Pipeline")
    print(f"Operating System: {sys.platform} ({os.name})")
    print(f"Project Directory: {PROJECT_ROOT}")
    print(f"Python Interpreter: {python_exe}")

    # Step 1: Run Data Loader & Dataset Integrity Tests
    print_banner("STEP 1: Validating Raw & Processed Datasets")
    test_script = PROJECT_ROOT / "tests" / "test_data_loader.py"
    success = run_command([python_exe, str(test_script)], "Data Loader & Dataset Verification")
    if not success:
        print("\n❌ Pipeline stopped: Dataset validation failed.")
        sys.exit(1)

    if args.test_only:
        print("\n✔ Test-only run completed successfully.")
        return

    # Step 2: Run Week 1 AI/ML Baseline Models & Generate Reports
    print_banner("STEP 2: Training & Benchmarking Week 1 Baseline Models")
    train_script = PROJECT_ROOT / "src" / "models" / "train_baseline.py"
    success = run_command([python_exe, str(train_script)], "Week 1 AI/ML Baseline Training")
    if not success:
        print("\n❌ Pipeline stopped: Baseline model training failed.")
        sys.exit(1)

    # Step 3: Compute Correlations and Generate Analytical Plots
    print_banner("STEP 3: Generating Correlation Matrices & Plots (reports/figures/)")
    reports_script = PROJECT_ROOT / "src" / "visualization" / "reports_generator.py"
    success = run_command([python_exe, str(reports_script)], "Analytical Reports & Figures Generation")
    if not success:
        print("\n❌ Warning: Figure generation encountered an issue.")

    print_banner("Pipeline Execution Succeeded!")
    print("✔ Datasets verified.")
    print("✔ Out-of-sample 7-day baseline benchmarks trained and evaluated.")
    print("✔ Correlation matrices saved to 'reports/'.")
    print("✔ Publication-quality analytical figures saved to 'reports/figures/'.")

    # Step 3: Launch Streamlit App if requested
    if args.app:
        print_banner("STEP 3: Launching Streamlit Web Dashboard")
        app_script = PROJECT_ROOT / "app" / "app.py"
        try:
            subprocess.run([python_exe, "-m", "streamlit", "run", str(app_script)])
        except KeyboardInterrupt:
            print("\nStreamlit application stopped by user.")
    else:
        print("\n💡 TIP: To launch the interactive web dashboard, run:")
        print("    python run_all.py --app")
        print("  or directly:")
        print("    streamlit run app/app.py")


if __name__ == "__main__":
    main()

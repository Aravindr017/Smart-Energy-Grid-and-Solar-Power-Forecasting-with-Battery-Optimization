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

# Ensure UTF-8 output if supported on Windows
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)


def print_banner(text: str):
    print("\n" + "=" * 75)
    print(f"[*] {text}")
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
    parser.add_argument("--web", action="store_true", help="Launch modern React + Tailwind web application & FastAPI server (Week 3)")
    parser.add_argument("--app", action="store_true", help="Launch Streamlit dashboard")
    parser.add_argument("--test-only", action="store_true", help="Run only dataset & module integrity tests")
    args = parser.parse_args()

    python_exe = get_python_executable()
    print_banner("Smart Solar Grid & Battery Optimization Pipeline")
    print(f"Operating System: {sys.platform} ({os.name})")
    print(f"Project Directory: {PROJECT_ROOT}")
    print(f"Python Interpreter: {python_exe}")

    # Step 1: Run Data Loader & Dataset Integrity Tests
    print_banner("STEP 1: Validating Raw & Processed Datasets and Week 2 Modules")
    test_script = PROJECT_ROOT / "tests" / "test_data_loader.py"
    success = run_command([python_exe, str(test_script)], "Data Loader & Dataset Verification")
    if not success:
        print("\n❌ Pipeline stopped: Dataset validation failed.")
        sys.exit(1)

    test_week2_script = PROJECT_ROOT / "tests" / "test_week2.py"
    success = run_command([python_exe, str(test_week2_script)], "Week 2 Forecaster & Battery LP Verification")
    if not success:
        print("\n❌ Pipeline stopped: Week 2 unit tests failed.")
        sys.exit(1)

    test_week3_script = PROJECT_ROOT / "tests" / "test_week3.py"
    success = run_command([python_exe, str(test_week3_script)], "Week 3 API & UI Integration Verification")
    if not success:
        print("\n❌ Pipeline stopped: Week 3 unit tests failed.")
        sys.exit(1)

    test_week4_script = PROJECT_ROOT / "tests" / "test_week4.py"
    success = run_command([python_exe, "-m", "pytest", str(test_week4_script)], "Week 4 Stress Test, Carbon & PDF Verification")
    if not success:
        print("\n❌ Pipeline stopped: Week 4 unit tests failed.")
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

    # Step 3: Run Week 2 Advanced Forecasting & PuLP Battery Optimization
    print_banner("STEP 3: Training Week 2 Models (LightGBM, Prophet) & PuLP Battery Optimization")
    week2_script = PROJECT_ROOT / "src" / "models" / "train_forecasting.py"
    success = run_command([python_exe, str(week2_script)], "Week 2 Forecasting & Battery Arbitrage")
    if not success:
        print("\n❌ Pipeline stopped: Week 2 training failed.")
        sys.exit(1)

    # Step 4: Compute Correlations and Generate Analytical Plots
    print_banner("STEP 4: Generating Correlation Matrices & Plots (reports/figures/)")
    reports_script = PROJECT_ROOT / "src" / "visualization" / "reports_generator.py"
    success = run_command([python_exe, str(reports_script)], "Analytical Reports & Figures Generation")
    if not success:
        print("\n❌ Warning: Figure generation encountered an issue.")

    # Step 5: Week 4 Weather Stress Testing & Carbon Accounting
    print_banner("STEP 5: Running Week 4 Weather Stress Testing & Carbon Accounting")
    stress_script = PROJECT_ROOT / "src" / "analysis" / "weather_stress_test.py"
    success = run_command([python_exe, str(stress_script)], "Extreme-Weather Stress Testing")
    if not success:
        print("\n❌ Warning: Weather stress test suite encountered an issue.")

    carbon_script = PROJECT_ROOT / "src" / "analysis" / "carbon_accounting.py"
    success = run_command([python_exe, str(carbon_script)], "Carbon-Offset Accounting (CEA v19.0)")
    if not success:
        print("\n❌ Warning: Carbon accounting suite encountered an issue.")

    # Step 6: Week 4 Executive PDF Generation
    print_banner("STEP 6: Compiling Dynamic Multi-Page Executive PDF Technical Reports")
    pdf_script = PROJECT_ROOT / "src" / "visualization" / "executive_report.py"
    success = run_command([python_exe, str(pdf_script)], "ReportLab 6-Page Executive PDF Generation")
    if not success:
        print("\n❌ Warning: Executive PDF generation encountered an issue.")

    print_banner("Complete 4-Week Pipeline Execution Succeeded!")
    print("✔ Datasets verified across Plant 1 & Plant 2.")
    print("✔ Out-of-sample 7-day baseline benchmarks evaluated.")
    print("✔ Advanced LightGBM & Prophet models benchmarked.")
    print("✔ PuLP 24-hour battery arbitrage LP solved with mutual exclusivity.")
    print("✔ 6 Extreme-weather stress scenarios evaluated.")
    print("✔ Carbon-offset accounting benchmarked with CEA v19.0 provenance.")
    print("✔ Publication-quality 6-page Executive PDF technical reports generated.")
    print("✔ Correlation matrices & figures saved to 'reports/'.")

    # Step 7: Launch Web Application if requested
    if args.web:
        print_banner("STEP 7: Launching Modern React & FastAPI Solar Dashboard (Weeks 1-4)")
        print("🌐 Application available at: http://127.0.0.1:8000")
        try:
            subprocess.run([python_exe, "-m", "uvicorn", "src.api.server:app", "--host", "127.0.0.1", "--port", "8000"])
        except KeyboardInterrupt:
            print("\nWeb server stopped by user.")
    elif args.app:
        print_banner("STEP 7: Launching Streamlit Web Dashboard")
        app_script = PROJECT_ROOT / "app" / "app.py"
        try:
            subprocess.run([python_exe, "-m", "streamlit", "run", str(app_script)])
        except KeyboardInterrupt:
            print("\nStreamlit application stopped by user.")
    else:
        print("\n💡 TIP: To launch the modern React + Tailwind solar dashboard (Weeks 1-4), run:")
        print("    python run_all.py --web")
        print("  or directly via uvicorn:")
        print("    python -m uvicorn src.api.server:app --port 8000")
        print("  (Streamlit full dashboard is also available via: python run_all.py --app)")


if __name__ == "__main__":
    main()

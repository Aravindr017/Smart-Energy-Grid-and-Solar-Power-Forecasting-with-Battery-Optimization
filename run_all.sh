#!/usr/bin/env bash
# ==============================================================================
# Unix / macOS / Linux Runner Script
# Smart Energy Grid & Solar Power Forecasting with Battery Optimization
# ==============================================================================

set -e

# Navigate to script directory
cd "$(dirname "$0")"

# Detect Python interpreter
if [ -f "./venv/bin/python" ]; then
    PYTHON_BIN="./venv/bin/python"
elif [ -f "./.venv/bin/python" ]; then
    PYTHON_BIN="./.venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
else
    PYTHON_BIN="python"
fi

echo "Using Python: $PYTHON_BIN"
$PYTHON_BIN run_all.py "$@"

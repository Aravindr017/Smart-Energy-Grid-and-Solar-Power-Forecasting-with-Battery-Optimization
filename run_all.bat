@echo off
REM ==============================================================================
REM Windows Batch Runner Script
REM Smart Energy Grid & Solar Power Forecasting with Battery Optimization
REM ==============================================================================

cd /d "%~dp0"

IF EXIST "venv\Scripts\python.exe" (
    SET "PYTHON_BIN=venv\Scripts\python.exe"
) ELSE IF EXIST ".venv\Scripts\python.exe" (
    SET "PYTHON_BIN=.venv\Scripts\python.exe"
) ELSE (
    SET "PYTHON_BIN=python"
)

echo Using Python: %PYTHON_BIN%
%PYTHON_BIN% run_all.py %*
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo Pipeline encountered an error.
    pause
)

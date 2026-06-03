@echo off
setlocal
cd /d "%~dp0"

python --version >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Please install Python 3.12 and try again.
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>nul
if errorlevel 1 (
    echo Installing project dependencies from requirements.txt...
    python -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo Dependency installation failed.
        pause
        exit /b 1
    )
)

echo Starting PV forecasting dashboard...
python -m streamlit run "%~dp0app.py"
pause

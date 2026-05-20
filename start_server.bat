@echo off
title UPI Fraud Detector - Server
color 0A
cls

echo ============================================
echo   UPI FRAUD DETECTOR v5.0 - SERVER START
echo ============================================
echo.

REM === Project folder ki navigate cheyyandi ===
cd /d "%~dp0"

echo [1/3] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python install avvaledu!
    echo Download: https://www.python.org/downloads/
    pause
    exit
)

echo [2/3] Activating virtual environment...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo      venv activated!
) else (
    echo      venv ledu - system Python use avutundi
)

echo [3/3] Checking required files...
if not exist "fraud_model.pkl" (
    echo.
    echo WARNING: fraud_model.pkl ledu!
    echo Running train_model.py first...
    echo.
    if not exist "transactions.csv" (
        echo Generating training data...
        python generate_data.py
    )
    python train_model.py
    echo.
)

if not exist ".env" (
    echo WARNING: .env file ledu! Creating default...
    (
        echo SECRET_KEY=upi_fraud_secret_key_change_in_production
        echo ALGORITHM=HS256
        echo ACCESS_TOKEN_EXPIRE_MINUTES=60
        echo DATABASE_URL=sqlite:///./fraud.db
    ) > .env
    echo .env file created!
    echo.
)

echo.
echo ============================================
echo   SERVER STARTING on http://127.0.0.1:8001
echo ============================================
echo.
echo  Dashboard: http://127.0.0.1:8001/dashboard
echo  API Docs:  http://127.0.0.1:8001/docs
echo  Login:     admin / Admin@123
echo.
echo  Server band cheyyalanante Ctrl+C press cheyyandi
echo ============================================
echo.

python -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload

pause

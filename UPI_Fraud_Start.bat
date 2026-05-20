@echo off
title UPI Fraud Detector v5.0
color 0A
cls

echo ============================================
echo   UPI FRAUD DETECTOR v5.0 - STARTING...
echo ============================================
echo.

cd /d "C:\Users\rajac\OneDrive\Desktop\upi-fraud-detector"

echo Stopping any existing server...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo Starting server...
echo.
echo  Dashboard: http://127.0.0.1:8001/dashboard
echo  Login:     admin / Admin@123
echo.
echo ============================================
echo  CMD close cheyyakandi - server band avutundhi!
echo ============================================
echo.

py -3.11 -m uvicorn app:app --port 8001

pause

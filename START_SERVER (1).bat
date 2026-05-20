@echo off
title UPI Fraud Detector v5.0
color 0A
cls

echo ============================================
echo   UPI FRAUD DETECTOR v5.0
echo ============================================
echo.
echo  Server starting...
echo.

cd /d "C:\Users\rajac\OneDrive\Desktop\upi-fraud-detector"

py -3.11 -m uvicorn app:app --port 8001

pause

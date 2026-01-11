@echo off
REM QuantDSF v2 Startup Script for Windows
REM ========================================

echo.
echo ============================================================
echo   QuantDSF v2 - nanoDSF Analysis Platform
echo   Starting application...
echo ============================================================
echo.

REM Activate virtual environment
call .venv312\Scripts\activate.bat

REM Start the application on port 9050
python app_v2.py --port 9050 --host 127.0.0.1

pause

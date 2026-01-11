@echo off
REM Run ingestion with interactive file picker dialogs

echo.
echo ========================================================================
echo    ECOMMERCE ANALYTICS - Data Ingestion With Interactive Picker
echo ========================================================================
echo.
echo This script will open file picker dialogs to select input files:
echo   1. PRODUCTS (Excel) - REQUIRED
echo   2. ORDERS (CSV)     - OPTIONAL (you can cancel)
echo   3. RETURNS (CSV)    - OPTIONAL (you can cancel)
echo.
echo Press any key to continue...
pause > nul

if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo.
python run_all_ingest.py --use-dialog

echo.
echo ========================================================================
pause

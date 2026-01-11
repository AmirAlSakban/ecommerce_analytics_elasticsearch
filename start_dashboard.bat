@echo off
REM Start Streamlit dashboard without running ingestion

echo.
echo ========================================================================
echo    STREAMLIT DASHBOARD - Start Without Ingestion
echo ========================================================================
echo.
echo Starting Streamlit dashboard at http://localhost:8501
echo.
echo ⚠️  The dashboard will display data that already exists in Elasticsearch.
echo    If you want to ingest new data, run: ./run_ingest_with_picker.bat
echo.
echo ========================================================================
echo.

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
streamlit run app\streamlit_app.py

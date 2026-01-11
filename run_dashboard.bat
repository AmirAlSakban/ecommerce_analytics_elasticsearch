@echo off
setlocal
cd /d %~dp0
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

if "%1"=="--no-ingest" (
    shift
    goto RUN_APP
)

echo [INFO] Running full ingestion (run_all_ingest.py)
python run_all_ingest.py
if errorlevel 1 goto END

:RUN_APP
echo [INFO] Starting Streamlit dashboard
streamlit run app\streamlit_app.py

:END
endlocal

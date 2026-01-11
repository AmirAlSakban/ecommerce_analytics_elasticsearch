@echo off
setlocal
cd /d %~dp0
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat >nul 2>&1
)
echo Starting FastAPI server on http://localhost:8000 ...
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

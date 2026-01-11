@echo off
REM Start Elasticsearch server

echo.
echo ========================================================================
echo    ELASTICSEARCH - Start Server
echo ========================================================================
echo.

set ES_PATH=out\elasticsearch\elasticsearch-8.15.2

if not exist %ES_PATH%\bin\elasticsearch.bat (
    echo ❌ ERROR: Could not find Elasticsearch at: %ES_PATH%
    echo.
    echo Verify that Elasticsearch is installed in the correct folder.
    echo.
    pause
    exit /b 1
)

echo Elasticsearch directory: %ES_PATH%
echo.
echo Starting Elasticsearch...
echo.
echo ⚠️  IMPORTANT: Do not close this terminal!
echo    Elasticsearch will run here and print logs.
echo    To stop the server, press Ctrl+C in this terminal.
echo.
echo ========================================================================
echo.

cd %ES_PATH%
bin\elasticsearch.bat

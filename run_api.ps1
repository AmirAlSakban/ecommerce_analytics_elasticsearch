param(
    [int]$Port = 8000,
    [string]$ListenHost = "0.0.0.0"
)

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptRoot

$venvActivate = Join-Path $scriptRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvActivate) {
    . $venvActivate
}

Write-Host "Starting FastAPI server on http://$ListenHost`:$Port ..."
python -m uvicorn api.main:app --host $ListenHost --port $Port --reload

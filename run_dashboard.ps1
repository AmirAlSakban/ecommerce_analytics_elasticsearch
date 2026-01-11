param(
    [switch]$NoIngest
)

Set-Location $PSScriptRoot
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"

if (-not $NoIngest) {
    Write-Host "[INFO] Rulez ingestia completă (run_all_ingest.py)"
    python run_all_ingest.py
    if ($LASTEXITCODE -ne 0) {
        throw "run_all_ingest.py a eșuat"
    }
} else {
    Write-Host "[INFO] Sari peste ingestie la rularea dashboard-ului"
}

Write-Host "[INFO] Pornez dashboard-ul Streamlit"
streamlit run app/streamlit_app.py

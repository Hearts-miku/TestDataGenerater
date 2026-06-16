# Production startup — build frontend then serve via FastAPI
param(
    [int]$Port = 8000
)

Set-Location $PSScriptRoot\..

Write-Host "Building frontend..."
Set-Location frontend
pnpm build
if ($LASTEXITCODE -ne 0) { Write-Error "Frontend build failed"; exit 1 }
Set-Location ..

Write-Host "Starting DataForge on http://localhost:$Port"
Set-Location backend
$env:DATAFORGE_DUCKDB_PATH = "data/dataforge.duckdb"
uv run uvicorn main:app --host 0.0.0.0 --port $Port

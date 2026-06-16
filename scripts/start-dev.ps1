# Dev startup — backend on :8000, Vite HMR on :5173
Set-Location $PSScriptRoot\..

# Start backend
$backend = Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$((Get-Location).Path)\backend'; `$env:DATAFORGE_DUCKDB_PATH='data/dataforge.duckdb'; uv run uvicorn main:app --port 8000 --reload" `
    -PassThru

Write-Host "Backend PID: $($backend.Id) — http://localhost:8000"

# Start frontend dev server
$frontend = Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "cd '$((Get-Location).Path)\frontend'; pnpm dev" `
    -PassThru

Write-Host "Frontend PID: $($frontend.Id) — http://localhost:5173"
Write-Host ""
Write-Host "Press Ctrl+C to stop..."

try {
    Wait-Process -Id $backend.Id, $frontend.Id
} finally {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
}

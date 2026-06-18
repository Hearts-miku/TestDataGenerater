# Dev startup — backend on :8000, Vite HMR on :5173
$ErrorActionPreference = "Stop"

$root = Resolve-Path "$PSScriptRoot\.."

function Check-Command($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: $name not found. $hint" -ForegroundColor Red
        Write-Host "Press Enter to exit..."
        $null = Read-Host
        exit 1
    }
}

Check-Command "uv"   "Install with: pip install uv"
Check-Command "pnpm" "Install with: npm install -g pnpm"

# Start backend in a new window
$backendCmd = "cd '$root\backend'; `$env:DATAFORGE_DUCKDB_PATH='data/dataforge.duckdb'; uv run uvicorn main:app --port 8000 --reload; Write-Host 'Backend exited.'; Read-Host 'Press Enter to close'"
$backend = Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -PassThru

Write-Host "Backend PID: $($backend.Id) — http://localhost:8000" -ForegroundColor Cyan

# Start frontend dev server in a new window
$frontendCmd = "cd '$root\frontend'; pnpm dev; Write-Host 'Frontend exited.'; Read-Host 'Press Enter to close'"
$frontend = Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -PassThru

Write-Host "Frontend PID: $($frontend.Id) — http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Both servers are running in separate windows." -ForegroundColor Green
Write-Host "Press Ctrl+C here to stop both, or close their windows manually."
Write-Host ""

try {
    # Wait for either process to exit
    while (-not $backend.HasExited -and -not $frontend.HasExited) {
        Start-Sleep -Seconds 2
    }
} finally {
    Stop-Process -Id $backend.Id  -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
}

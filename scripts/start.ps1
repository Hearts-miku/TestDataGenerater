# Production startup — build frontend then serve via FastAPI
param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

function Pause-OnError {
    Write-Host ""
    Write-Host "Press Enter to exit..." -ForegroundColor Red
    $null = Read-Host
    exit 1
}

$root = Resolve-Path "$PSScriptRoot\.."

# ── Build frontend ────────────────────────────────────────────────────────────
Write-Host "Building frontend..." -ForegroundColor Cyan
Set-Location "$root\frontend"

if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: pnpm not found. Install with: npm install -g pnpm" -ForegroundColor Red
    Pause-OnError
}

pnpm build
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Frontend build failed (exit code $LASTEXITCODE)" -ForegroundColor Red
    Pause-OnError
}

# ── Start backend ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Starting DataForge on http://localhost:$Port" -ForegroundColor Green
Set-Location "$root\backend"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: uv not found. Install with: pip install uv" -ForegroundColor Red
    Pause-OnError
}

$env:DATAFORGE_DUCKDB_PATH = "data/dataforge.duckdb"

# ── Pre-flight: ensure the port is free ───────────────────────────────────────
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    $pids = ($busy.OwningProcess | Select-Object -Unique) -join ", "
    Write-Host "ERROR: Port $Port is already in use by PID(s): $pids" -ForegroundColor Red
    Write-Host "Free it with:  Stop-Process -Id $pids -Force" -ForegroundColor Yellow
    Write-Host "Or start on another port:  .\scripts\start.ps1 -Port 8001" -ForegroundColor Yellow
    Pause-OnError
}

try {
    uv run uvicorn main:app --host 0.0.0.0 --port $Port
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    Pause-OnError
}

# Keep window open if server exits unexpectedly
if ($LASTEXITCODE -ne 0) {
    Write-Host "Server exited with code $LASTEXITCODE" -ForegroundColor Yellow
    Write-Host "Press Enter to close..."
    $null = Read-Host
}

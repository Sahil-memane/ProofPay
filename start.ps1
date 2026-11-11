# ProofPay — Start Script
# Builds React frontend (if needed) and starts FastAPI

param(
    [switch]$Dev,     # Run Vite dev server separately
    [switch]$NoBuild  # Skip React build (use existing dist/)
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "`n🛡️  ProofPay Startup" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan

# 1. Build frontend (unless skipped)
if (-not $NoBuild) {
    Write-Host "`n📦 Building React frontend..." -ForegroundColor Yellow
    Push-Location "$root\frontend\react-app"
    npm run build
    Pop-Location
    Write-Host "✓ Frontend built" -ForegroundColor Green
}

# 2. Start FastAPI
Write-Host "`n🚀 Starting FastAPI server on http://localhost:8000" -ForegroundColor Yellow
Write-Host "   → React SPA:   http://localhost:8000/" -ForegroundColor Gray
Write-Host "   → API Docs:    http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "   → Health:      http://localhost:8000/healthz" -ForegroundColor Gray
Write-Host ""

Set-Location $root
python -m uvicorn backend.app.main:app --port 8000 --reload


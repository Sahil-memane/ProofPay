#!/usr/bin/env bash
# ============================================================
# ProofPay — Render build script
# Runs during Render's build phase:
#   1. Install Python dependencies
#   2. Install Node + build React frontend into dist/
#   3. Run Alembic migrations
# ============================================================
set -e

echo "=== [1/3] Installing Python dependencies ==="
pip install --upgrade pip
pip install -e "."

echo "=== [2/3] Building React frontend ==="
# Use npm install (not npm ci) to handle any lock file drift across platforms
npm --prefix frontend/react-app install --no-fund --no-audit
# Build into frontend/react-app/dist — FastAPI mounts this automatically
npm --prefix frontend/react-app run build
echo "Frontend built to frontend/react-app/dist/"

echo "=== [3/3] Running Alembic database migrations ==="
# DATABASE_URL_SYNC must be set in Render env vars
# derive sync URL from DATABASE_URL if DATABASE_URL_SYNC is not set explicitly
if [ -z "$DATABASE_URL_SYNC" ]; then
  # Render provides postgresql:// URL — asyncpg needs postgresql+asyncpg://
  # For alembic (sync), strip "+asyncpg" if present and ensure it's plain postgresql://
  export DATABASE_URL_SYNC="${DATABASE_URL/+asyncpg/}"
fi
alembic upgrade head

echo "=== Build complete ==="


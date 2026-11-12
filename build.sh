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
# Alembic uses psycopg2 (sync). Coerce DATABASE_URL_SYNC to postgresql+psycopg2://
# so SQLAlchemy does not try to import psycopg (v3) which is not installed.
if [ -z "$DATABASE_URL_SYNC" ]; then
  # Start from raw DATABASE_URL (postgresql:// or postgresql+asyncpg://)
  _raw="${DATABASE_URL}"
else
  _raw="${DATABASE_URL_SYNC}"
fi
# Strip any driver suffix, then prepend +psycopg2
_bare="${_raw#postgresql+asyncpg://}"
_bare="${_bare#postgresql+psycopg2://}"
_bare="${_bare#postgresql://}"
_bare="${_bare#postgres://}"
export DATABASE_URL_SYNC="postgresql+psycopg2://${_bare}"
echo "Using DATABASE_URL_SYNC driver: postgresql+psycopg2"
alembic upgrade head

echo "=== Build complete ==="


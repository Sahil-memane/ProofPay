#!/bin/bash
# ProofPay — Start Script (Linux/Mac)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "🛡️  ProofPay Startup"
echo "==================="

# Build frontend
if [ "$1" != "--no-build" ]; then
  echo ""
  echo "📦 Building React frontend..."
  cd "$ROOT/frontend/react-app"
  npm run build
  cd "$ROOT"
  echo "✓ Frontend built"
fi

# Start FastAPI
echo ""
echo "🚀 Starting FastAPI on http://localhost:8000"
echo "   → React SPA:  http://localhost:8000/"
echo "   → API Docs:   http://localhost:8000/docs"
echo ""
python -m uvicorn backend.app.main:app --port 8000 --reload


#!/usr/bin/env python
"""Export FastAPI OpenAPI schema to contracts/openapi.json."""
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.main import app

OUTPUT = Path(__file__).resolve().parents[2] / "contracts" / "openapi.json"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

schema = app.openapi()
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2)

print(f"[OK] Written {len(schema.get('paths', {}))} paths to {OUTPUT}")


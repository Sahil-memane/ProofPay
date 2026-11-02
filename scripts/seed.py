#!/usr/bin/env python3
"""
Seed script: generate synthetic data with default seed=42.

Usage:
    python scripts/seed.py [--seed N] [--out-dir PATH] [--no-write]
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

# Make backend importable when run from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.simulator.datagen import generate


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ProofPay synthetic data")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default 42)")
    parser.add_argument("--out-dir", type=Path, default=None, help="Output directory for generated files")
    parser.add_argument("--answer-key-dir", type=Path, default=None, help="Output directory for answer key files")
    parser.add_argument("--no-write", action="store_true", help="Do not write files to disk")
    args = parser.parse_args()
    

    result = generate(
        seed=args.seed,
        out_dir=args.out_dir,
        answer_key_dir=args.answer_key_dir,
        write=not args.no_write,
    )
    custs = result["customers"]
    subs = result["subscriptions"]
    invs = result["invoices"]
    recs = result["records"]
    traps = result["traps"]
    print(f"Generated (seed={args.seed}):")
    print(f"  {len(custs)} customers")
    print(f"  {len(subs)} failed subscriptions")
    print(f"  {len(invs)} overdue invoices")
    print(f"  {recs.total_records} total records across 3 sources")
    print(f"  {len(result['escrow'])} escrow projects")
    print(f"  {len(traps)} traps planted")
    if result["written_paths"]:
        print("Written to:")
        for name, path in result["written_paths"].items():
            print(f"  [{name}] {path}")


if __name__ == "__main__":
    main()


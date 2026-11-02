#!/usr/bin/env python3
"""
CLI Script to run ProofPay Recovery Agent Benchmark Evaluation.

Usage:
  python backend/scripts/run_eval.py [--limit N] [--seed SEED]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.eval.report import generate_json_report, generate_markdown_report
from backend.app.eval.runner import run_evaluation
REPORT_MD = ROOT / "data" / "eval_report.md"
REPORT_JSON = ROOT / "data" / "eval_report.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ProofPay Evaluation Harness")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test cases")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for simulation")
    args = parser.parse_args()

    print(f"Running evaluation (seed={args.seed}, limit={args.limit})...")
    comparison = run_evaluation(cases_limit=args.limit, seed=args.seed)

    # Format reports
    md_content = generate_markdown_report(comparison)
    json_content = generate_json_report(comparison)

    # Write files
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write(md_content)

    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        f.write(json_content)

    print("\n" + md_content)
    print(f"\nSaved evaluation reports to:\n  - {REPORT_MD}\n  - {REPORT_JSON}")


if __name__ == "__main__":
    main()


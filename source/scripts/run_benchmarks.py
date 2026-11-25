"""CLI script to run Quality Audit, Mutation Testing, Harbor 0.25.x NOP/Oracle, and Final Report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.harbor_runner import HarborRunner
from core.quality_auditor import QualityAuditor
from dashboard.reports import generate_final_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Quality Audit, Mutation Testing, and Harbor Benchmarks.")
    parser.add_argument("--skip-harbor", action="store_true", help="Run only Quality & Mutation audits.")
    parser.add_argument("--skip-audit", action="store_true", help="Run only Harbor NOP & Oracle benchmarks.")
    args = parser.parse_args()

    if not args.skip_audit:
        print("=== Running Module F: Quality & Mutation Auditor ===")
        qa = QualityAuditor().run_all(save=True)
        print(
            f"Valid tasks: {qa['valid_tasks']}/{qa['total_tasks']} | "
            f"Overall mutation score: {qa['overall_mutation_score_pct']}%"
        )

    if not args.skip_harbor:
        print("=== Running Module G: Harbor 0.25.x NOP & Oracle Benchmark ===")
        br = HarborRunner().run_all(agents=("nop", "oracle"), save=True)
        print(f"Backend: {br['execution_backend']}")
        print(f"NOP rewards: {br['summary']['nop_rewards']}")
        print(f"Oracle rewards: {br['summary']['oracle_rewards']}")

    print("=== Generating Module H: FINAL_VERIFICATION_REPORT.md ===")
    generate_final_report(save=True)
    print("Completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

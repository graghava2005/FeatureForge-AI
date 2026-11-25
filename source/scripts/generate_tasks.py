"""CLI script to run Modules A-E and generate all five Harbor task packages."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.task_generator import TaskGenerator


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate five Harbor tasks for pallets/click.")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Enable optional OpenAI enrichment of problem descriptions (falls back automatically if unavailable).",
    )
    args = parser.parse_args()

    summary = TaskGenerator(use_llm_enrichment=args.llm).run(save=True)
    print(f"Repository: {summary['repository']} @ {summary['base_commit']}")
    print(f"Candidates evaluated: {summary['total_candidates_evaluated']}")
    print(f"Rejected candidates: {[r['task_id'] for r in summary['rejected_candidates']]}")
    print(f"Generated tasks ({summary['generated_task_count']}): {[t['task_id'] for t in summary['tasks']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

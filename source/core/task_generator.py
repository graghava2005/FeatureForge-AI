"""Task Package Generator: Assembles Harbor 0.25.x task directories for approved features."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

from harbor.models.task.config import TaskConfig

from config.settings import (
    BASE_COMMIT_SHA,
    GENERATED_TASKS_PATH,
    TARGET_REPO_DIR,
    TARGET_REPO_NAME,
    TARGET_REPO_URL,
    TASKS_DIR,
    ensure_directories,
)
from core.feature_generator import FeatureGenerator
from core.llm_client import LLMClient
from core.novelty_checker import NoveltyChecker
from core.oracle_generator import OracleGenerator
from core.repository_analyzer import RepositoryAnalyzer
from core.test_generator import TestGenerator


def _render_instruction_md(proposal: dict[str, Any], base_commit: str) -> str:
    reqs = "\n".join(f"- {r}" for r in proposal["user_requirements"])
    acs = "\n".join(f"- {a}" for a in proposal["acceptance_criteria"])
    scenarios = "\n".join(f"- {s}" for s in proposal["new_feature_test_scenarios"])
    reg_reqs = "\n".join(f"- {r}" for r in proposal["regression_test_requirements"])
    target_files = ", ".join(f"`{f}`" for f in proposal["target_files"])

    return (
        f"# Feature Development Task: {proposal['feature_title']}\n\n"
        f"**Repository:** `{TARGET_REPO_NAME}`  \n"
        f"**Base Commit:** `{base_commit}`  \n"
        f"**Subsystem:** `{proposal['subsystem']}`  \n"
        f"**Primary Target File(s):** {target_files}\n\n"
        f"## Problem Description\n\n"
        f"{proposal['problem_description']}\n\n"
        f"## Requirements\n\n"
        f"{reqs}\n\n"
        f"## Expected Behaviour\n\n"
        f"{proposal['expected_behaviour']}\n\n"
        f"## Acceptance Criteria\n\n"
        f"{acs}\n\n"
        f"## Feature Test Scenarios to Satisfy\n\n"
        f"{scenarios}\n\n"
        f"## Regression Constraints\n\n"
        f"{reg_reqs}\n"
        f"- Keep all changes clean, typed, and isolated to the feature scope.\n"
        f"- Do not modify existing test files unless required; preserve backward compatibility.\n"
    )


def _render_task_toml(proposal: dict[str, Any], base_commit: str) -> str:
    task_id = proposal["task_id"]
    slug = proposal["slug"]
    title_escaped = proposal["feature_title"].replace('"', '\\"')
    return (
        'schema_version = "1.4"\n\n'
        "[task]\n"
        f'name = "featureforge/click-{slug}"\n'
        'version = "0.1.0"\n'
        f'description = "{title_escaped}"\n'
        f'keywords = ["python", "click", "feature-development", "{proposal["subsystem"]}"]\n\n'
        "[metadata]\n"
        f'task_id = "{task_id}"\n'
        f'slug = "{slug}"\n'
        f'repository = "{TARGET_REPO_NAME}"\n'
        f'base_commit = "{base_commit}"\n'
        'category = "feature-development"\n'
        f'subsystem = "{proposal["subsystem"]}"\n'
        f'difficulty = "{proposal["difficulty"]}"\n'
        'language = "python"\n'
        'test_framework = "pytest"\n\n'
        "[verifier]\n"
        "timeout_sec = 300.0\n\n"
        "[agent]\n"
        "timeout_sec = 600.0\n\n"
        "[environment]\n"
        "build_timeout_sec = 600.0\n"
        "cpus = 2\n"
        "memory_mb = 2048\n"
        "storage_mb = 4096\n"
        'workdir = "/app"\n'
    )


def _render_dockerfile(base_commit: str) -> str:
    return (
        "FROM python:3.11-slim\n\n"
        "RUN apt-get update && apt-get install -y --no-install-recommends git bash && rm -rf /var/lib/apt/lists/*\n\n"
        "WORKDIR /app\n"
        f"RUN git clone {TARGET_REPO_URL} /app && \\\n"
        f"    git checkout {base_commit}\n\n"
        "RUN pip install --no-cache-dir -e . pytest\n"
    )


class TaskGenerator:
    """Generates complete, Harbor-valid task packages for five novel features."""

    def __init__(
        self,
        repo_dir: Path = TARGET_REPO_DIR,
        tasks_dir: Path = TASKS_DIR,
        use_llm_enrichment: bool = False,
    ) -> None:
        self.repo_dir = Path(repo_dir)
        self.tasks_dir = Path(tasks_dir)
        self.use_llm_enrichment = use_llm_enrichment
        self.analyzer = RepositoryAnalyzer(self.repo_dir)
        self.llm_client = LLMClient(enabled=True)
        self.feature_gen = FeatureGenerator(self.llm_client)
        self.novelty_checker = NoveltyChecker(self.repo_dir)
        self.oracle_gen = OracleGenerator(self.repo_dir)
        self.test_gen = TestGenerator()

    def run(self, save: bool = True) -> dict[str, Any]:
        ensure_directories()
        t0 = time.perf_counter()

        repo_analysis = self.analyzer.run(save=save)
        base_commit = repo_analysis["git_verification"]["head_sha"]
        if base_commit != BASE_COMMIT_SHA or len(base_commit) != 40:
            raise RuntimeError(
                f"Expected base commit {BASE_COMMIT_SHA}, got {base_commit!r}"
            )
        if not repo_analysis["git_verification"]["is_clean_working_tree"]:
            raise RuntimeError("Target repository working tree is dirty; cannot generate tasks.")

        cand_bundle = self.feature_gen.generate_candidates(
            repo_analysis, use_llm_enrichment=self.use_llm_enrichment
        )
        audit_result = self.novelty_checker.audit_candidates(cand_bundle["candidates"])
        approved = audit_result["approved_proposals"]
        if len(approved) != 5:
            raise RuntimeError(f"Expected 5 approved features, got {len(approved)}")

        generated_tasks: list[dict[str, Any]] = []
        for proposal in approved:
            task_id = proposal["task_id"]
            task_dir = self.tasks_dir / task_id
            if task_dir.exists():
                shutil.rmtree(task_dir)

            env_dir = task_dir / "environment"
            sol_dir = task_dir / "solution"
            tests_dir = task_dir / "tests"
            env_dir.mkdir(parents=True, exist_ok=True)
            sol_dir.mkdir(parents=True, exist_ok=True)
            tests_dir.mkdir(parents=True, exist_ok=True)

            instruction_md = _render_instruction_md(proposal, base_commit)
            task_toml = _render_task_toml(proposal, base_commit)
            # Validate task.toml using Harbor 0.25.x Pydantic schema
            validated_cfg = TaskConfig.model_validate_toml(task_toml)

            dockerfile = _render_dockerfile(base_commit)
            oracle = self.oracle_gen.generate_solution(task_id)
            tests = self.test_gen.generate_tests(task_id)

            (task_dir / "instruction.md").write_text(instruction_md, encoding="utf-8", newline="\n")
            (task_dir / "task.toml").write_text(task_toml, encoding="utf-8", newline="\n")
            (env_dir / "Dockerfile").write_text(dockerfile, encoding="utf-8", newline="\n")
            (sol_dir / "feature.patch").write_text(oracle["patch_text"], encoding="utf-8", newline="\n")
            (sol_dir / "solve.sh").write_text(oracle["solve_sh"], encoding="utf-8", newline="\n")

            (tests_dir / tests["feature_test_filename"]).write_text(
                tests["feature_test_code"], encoding="utf-8", newline="\n"
            )
            (tests_dir / "fail_to_pass.json").write_text(
                json.dumps(tests["fail_to_pass"], indent=2), encoding="utf-8", newline="\n"
            )
            (tests_dir / "pass_to_pass.json").write_text(
                json.dumps(tests["pass_to_pass"], indent=2), encoding="utf-8", newline="\n"
            )
            (tests_dir / "test.sh").write_text(tests["test_sh"], encoding="utf-8", newline="\n")

            generated_tasks.append(
                {
                    "task_id": task_id,
                    "slug": proposal["slug"],
                    "harbor_package_name": validated_cfg.task.name if validated_cfg.task else task_id,
                    "task_dir": str(task_dir),
                    "base_commit": base_commit,
                    "subsystem": proposal["subsystem"],
                    "feature_title": proposal["feature_title"],
                    "proposal": proposal,
                    "modified_files": oracle["modified_files"],
                    "feature_test_file": tests["feature_test_filename"],
                    "fail_to_pass_count": len(tests["fail_to_pass"]),
                    "pass_to_pass_targets": tests["pass_to_pass"],
                    "task_toml_valid": True,
                }
            )

        elapsed = round(time.perf_counter() - t0, 3)
        summary = {
            "repository": TARGET_REPO_NAME,
            "base_commit": base_commit,
            "llm_provider": cand_bundle["llm_provider"],
            "llm_model": cand_bundle["llm_model"],
            "llm_reason": cand_bundle["llm_reason"],
            "total_candidates_evaluated": audit_result["total_evaluated"],
            "rejected_candidates": audit_result["rejected_proposals"],
            "novelty_audit_records": audit_result["audit_records"],
            "generated_task_count": len(generated_tasks),
            "tasks": generated_tasks,
            "generation_duration_sec": elapsed,
        }

        if save:
            GENERATED_TASKS_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        return summary

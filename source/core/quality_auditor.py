"""Module F2: Six-Dimension Quality Auditor."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from harbor.models.task.config import TaskConfig

from config.settings import (
    BASE_COMMIT_SHA,
    GENERATED_TASKS_PATH,
    QUALITY_REPORT_PATH,
    TARGET_REPO_DIR,
    TASKS_DIR,
    ensure_directories,
)
from core.mutation_tester import MutationTester


class QualityAuditor:
    """Runs requirement consistency, coverage, regression, mutation, isolation, and determinism checks."""

    def __init__(
        self,
        repo_dir: Path = TARGET_REPO_DIR,
        tasks_dir: Path = TASKS_DIR,
    ) -> None:
        self.repo_dir = Path(repo_dir)
        self.tasks_dir = Path(tasks_dir)
        self.mutation_tester = MutationTester(self.repo_dir, self.tasks_dir)

    def _run_pytest(self, cwd: Path, targets: list[str]) -> tuple[int, str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = str((cwd / "src").resolve())
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *targets, "-q", "--tb=short"],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    def _make_worktree(self, patch_path: Path | None) -> Path:
        wt = Path(tempfile.mkdtemp(prefix="ff_qa_"))
        shutil.copytree(
            self.repo_dir,
            wt,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
        )
        if patch_path is not None:
            subprocess.run(
                ["git", "-c", "safe.directory=*", "-C", str(wt), "apply", str(patch_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        return wt

    def audit_task(
        self,
        task_dir: Path,
        proposal: dict[str, Any] | None = None,
        mutation_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tid = task_dir.name
        t0 = time.perf_counter()

        required_files = [
            task_dir / "instruction.md",
            task_dir / "task.toml",
            task_dir / "environment" / "Dockerfile",
            task_dir / "solution" / "solve.sh",
            task_dir / "solution" / "feature.patch",
            task_dir / "tests" / "test.sh",
            task_dir / "tests" / "fail_to_pass.json",
            task_dir / "tests" / "pass_to_pass.json",
        ]
        missing_files = [str(p.relative_to(task_dir)) for p in required_files if not p.exists()]
        test_files = list((task_dir / "tests").glob("test_feature_*.py"))
        if not test_files:
            missing_files.append("tests/test_feature_*.py")

        # Validate task.toml via Harbor 0.25.x schema
        toml_valid = False
        base_commit_recorded = False
        try:
            cfg = TaskConfig.model_validate_toml((task_dir / "task.toml").read_text(encoding="utf-8"))
            toml_valid = True
            base_commit_recorded = cfg.metadata.get("base_commit") == BASE_COMMIT_SHA
        except Exception:
            pass

        fail_to_pass = json.loads((task_dir / "tests" / "fail_to_pass.json").read_text(encoding="utf-8"))
        pass_to_pass = json.loads((task_dir / "tests" / "pass_to_pass.json").read_text(encoding="utf-8"))
        feature_test = test_files[0]

        # Check 1: Requirement-test consistency
        ac_count = len(proposal.get("acceptance_criteria", [])) if proposal else len(fail_to_pass)
        req_test_consistent = (
            len(fail_to_pass) >= 6
            and len(pass_to_pass) >= 2
            and len(missing_files) == 0
            and toml_valid
            and base_commit_recorded
        )

        # Check 2 & 3 & 5 & 6 using base worktree and patched worktree
        base_wt = self._make_worktree(None)
        patched_wt = self._make_worktree(task_dir / "solution" / "feature.patch")
        try:
            base_feat_copy = base_wt / "tests" / feature_test.name
            patched_feat_copy = patched_wt / "tests" / feature_test.name
            shutil.copy2(feature_test, base_feat_copy)
            shutil.copy2(feature_test, patched_feat_copy)
            rel_feat = f"tests/{feature_test.name}"

            base_feat_rc, base_feat_out = self._run_pytest(base_wt, [rel_feat])
            base_reg_rc, _ = self._run_pytest(base_wt, pass_to_pass)

            patched_feat_rc_1, patched_feat_out_1 = self._run_pytest(patched_wt, [rel_feat])
            patched_feat_rc_2, patched_feat_out_2 = self._run_pytest(patched_wt, [rel_feat])
            patched_reg_rc, patched_reg_out = self._run_pytest(patched_wt, pass_to_pass)

            # Isolation check: run tests in reverse node order
            reversed_nodes = [
                f"{rel_feat}::{node.split('::', 1)[1]}" for node in reversed(fail_to_pass)
            ]
            iso_rc, iso_out = self._run_pytest(patched_wt, reversed_nodes)
        finally:
            shutil.rmtree(base_wt, ignore_errors=True)
            shutil.rmtree(patched_wt, ignore_errors=True)

        feature_coverage_ok = (base_feat_rc != 0) and (patched_feat_rc_1 == 0)
        regression_safety_ok = (base_reg_rc == 0) and (patched_reg_rc == 0)
        isolation_ok = iso_rc == 0

        summary_1 = patched_feat_out_1.strip().splitlines()[-1] if patched_feat_out_1.strip() else ""
        summary_2 = patched_feat_out_2.strip().splitlines()[-1] if patched_feat_out_2.strip() else ""
        # Strip timing token ("in 0.12s") when comparing deterministic pass counts
        norm_1 = summary_1.split(" in ")[0]
        norm_2 = summary_2.split(" in ")[0]
        deterministic_ok = (patched_feat_rc_1 == patched_feat_rc_2 == 0) and (norm_1 == norm_2)

        if mutation_result is None:
            mutation_result = self.mutation_tester.run_for_task(tid)
        mutation_ok = mutation_result.get("survived", 1) == 0 and mutation_result.get("killed", 0) > 0

        checks = {
            "1_requirement_test_consistency": {
                "passed": req_test_consistent,
                "acceptance_criteria_count": ac_count,
                "fail_to_pass_count": len(fail_to_pass),
                "pass_to_pass_count": len(pass_to_pass),
                "task_toml_valid": toml_valid,
                "base_commit_recorded": base_commit_recorded,
                "missing_files": missing_files,
            },
            "2_feature_coverage": {
                "passed": feature_coverage_ok,
                "base_feature_returncode": base_feat_rc,
                "patched_feature_returncode": patched_feat_rc_1,
                "base_summary": base_feat_out.strip().splitlines()[-1] if base_feat_out.strip() else "",
                "patched_summary": summary_1,
            },
            "3_regression_safety": {
                "passed": regression_safety_ok,
                "base_regression_returncode": base_reg_rc,
                "patched_regression_returncode": patched_reg_rc,
                "regression_targets": pass_to_pass,
                "patched_regression_summary": patched_reg_out.strip().splitlines()[-1]
                if patched_reg_out.strip()
                else "",
            },
            "4_mutation_testing": {
                "passed": mutation_ok,
                "total_mutants": mutation_result.get("total_mutants", 0),
                "killed": mutation_result.get("killed", 0),
                "survived": mutation_result.get("survived", 0),
                "mutation_score_pct": mutation_result.get("mutation_score_pct", 0.0),
            },
            "5_test_isolation": {
                "passed": isolation_ok,
                "reversed_order_returncode": iso_rc,
                "reversed_summary": iso_out.strip().splitlines()[-1] if iso_out.strip() else "",
            },
            "6_deterministic_execution": {
                "passed": deterministic_ok,
                "run_1_summary": summary_1,
                "run_2_summary": summary_2,
            },
        }

        all_passed = all(c["passed"] for c in checks.values())
        failed_checks = [k for k, v in checks.items() if not v["passed"]]

        return {
            "task_id": tid,
            "overall_passed": all_passed,
            "failed_checks": failed_checks,
            "duration_sec": round(time.perf_counter() - t0, 2),
            "checks": checks,
        }

    def run_all(self, task_ids: list[str] | None = None, save: bool = True) -> dict[str, Any]:
        ensure_directories()
        t0 = time.perf_counter()

        proposals_by_id: dict[str, dict[str, Any]] = {}
        if GENERATED_TASKS_PATH.exists():
            gen_data = json.loads(GENERATED_TASKS_PATH.read_text(encoding="utf-8"))
            for t_entry in gen_data.get("tasks", []):
                proposals_by_id[t_entry["task_id"]] = t_entry.get("proposal", {})

        mutation_report = self.mutation_tester.run_all(task_ids=task_ids, save=save)
        mut_by_id = {m["task_id"]: m for m in mutation_report["tasks"]}

        task_dirs = sorted(
            p for p in self.tasks_dir.iterdir()
            if p.is_dir() and (task_ids is None or p.name in task_ids)
        )

        task_audits = [
            self.audit_task(
                td,
                proposal=proposals_by_id.get(td.name),
                mutation_result=mut_by_id.get(td.name),
            )
            for td in task_dirs
        ]

        report = {
            "total_tasks": len(task_audits),
            "valid_tasks": sum(1 for t in task_audits if t["overall_passed"]),
            "overall_mutation_score_pct": mutation_report["overall_mutation_score_pct"],
            "duration_sec": round(time.perf_counter() - t0, 2),
            "tasks": task_audits,
        }

        if save:
            QUALITY_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

"""Module F1: Deliberate Code Mutation Tester."""

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

from config.settings import (
    BASE_COMMIT_SHA,
    MUTATION_REPORT_PATH,
    TARGET_REPO_DIR,
    TASKS_DIR,
    ensure_directories,
)


def _mutants_catalog() -> dict[str, list[dict[str, str]]]:
    return {
        "task_01": [
            {
                "id": "M1_disable_conflicts_with",
                "file": "src/click/core.py",
                "description": "Disable mutual-exclusivity check in _validate_option_constraints",
                "target": "if other_name != param.name and _is_explicit(other_name):",
                "replacement": "if False and other_name != param.name and _is_explicit(other_name):",
            },
            {
                "id": "M2_disable_requires",
                "file": "src/click/core.py",
                "description": "Disable required-partner check in _validate_option_constraints",
                "target": "if req_name != param.name and not _is_satisfied(req_name):",
                "replacement": "if False and req_name != param.name and not _is_satisfied(req_name):",
            },
            {
                "id": "M3_skip_constraint_name_norm",
                "file": "src/click/core.py",
                "description": "Skip dash-to-underscore normalization for CLI-style constraint names",
                "target": 'return name.strip().lstrip("-").replace("-", "_")',
                "replacement": "return name.strip()",
            },
        ],
        "task_02": [
            {
                "id": "M1_disable_alias_lookup",
                "file": "src/click/core.py",
                "description": "Disable alias match inside Group._resolve_alias",
                "target": "if target == candidate:",
                "replacement": "if False and target == candidate:",
            },
            {
                "id": "M2_disable_collision_check",
                "file": "src/click/core.py",
                "description": "Bypass alias collision validation in Group.add_command",
                "target": "if alias == existing_name or alias in existing_cmd.aliases:",
                "replacement": "if False and (alias == existing_name or alias in existing_cmd.aliases):",
            },
            {
                "id": "M3_omit_help_aliases",
                "file": "src/click/core.py",
                "description": "Hide command aliases in Group.format_commands help listing",
                "target": 'if cmd.aliases:\n                display_name = f"{subcommand} ({\', \'.join(cmd.aliases)})"',
                "replacement": 'if False and cmd.aliases:\n                display_name = f"{subcommand} ({\', \'.join(cmd.aliases)})"',
            },
        ],
        "task_03": [
            {
                "id": "M1_ignore_si_decimal_mode",
                "file": "src/click/types.py",
                "description": "Force binary base 1024 even when binary=False",
                "target": "base = 1024 if self.binary else 1000",
                "replacement": "base = 1024",
            },
            {
                "id": "M2_skip_min_bound",
                "file": "src/click/types.py",
                "description": "Disable minimum byte-size bound validation",
                "target": "if self.min is not None and result < self.min:",
                "replacement": "if False and self.min is not None and result < self.min:",
            },
            {
                "id": "M3_accept_booleans",
                "file": "src/click/types.py",
                "description": "Allow Python bool values to pass ByteSize.convert as ints",
                "target": "if isinstance(value, bool):",
                "replacement": "if False and isinstance(value, bool):",
            },
        ],
        "task_04": [
            {
                "id": "M1_ignore_no_color",
                "file": "src/click/_compat.py",
                "description": "Ignore NO_COLOR environment variable",
                "target": 'if os.environ.get("NO_COLOR", ""):',
                "replacement": 'if False and os.environ.get("NO_COLOR", ""):',
            },
            {
                "id": "M2_ignore_force_color",
                "file": "src/click/_compat.py",
                "description": "Ignore FORCE_COLOR environment variable",
                "target": 'if force_color and force_color.strip().lower() not in {"0", "false"}:',
                "replacement": 'if False and force_color and force_color.strip().lower() not in {"0", "false"}:',
            },
            {
                "id": "M3_skip_context_color_override",
                "file": "src/click/globals.py",
                "description": "Ignore explicit ctx.color when resolve_color_default runs",
                "target": "if ctx is not None and ctx.color is not None:",
                "replacement": "if False and ctx is not None and ctx.color is not None:",
            },
        ],
        "task_05": [
            {
                "id": "M1_break_ansi_width",
                "file": "src/click/termui.py",
                "description": "Use raw len(text) instead of ANSI-aware term_len in _align_cell",
                "target": "visible = term_len(text)",
                "replacement": "visible = len(text)",
            },
            {
                "id": "M2_disable_truncation",
                "file": "src/click/termui.py",
                "description": "Skip max_col_width cell truncation",
                "target": "if term_len(text) <= max_col_width:",
                "replacement": "if True or term_len(text) <= max_col_width:",
            },
            {
                "id": "M3_break_grid_border",
                "file": "src/click/termui.py",
                "description": "Disable grid border rendering branch",
                "target": 'if border == "grid":',
                "replacement": 'if False and border == "grid":',
            },
        ],
    }


class MutationTester:
    """Applies deliberate mutations to reference patches and checks if tests kill them."""

    def __init__(
        self,
        repo_dir: Path = TARGET_REPO_DIR,
        tasks_dir: Path = TASKS_DIR,
    ) -> None:
        self.repo_dir = Path(repo_dir)
        self.tasks_dir = Path(tasks_dir)

    def _prepare_patched_worktree(self, patch_path: Path) -> Path:
        worktree = Path(tempfile.mkdtemp(prefix="ff_mut_"))
        shutil.copytree(
            self.repo_dir,
            worktree,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
        )
        subprocess.run(
            ["git", "-c", "safe.directory=*", "-C", str(worktree), "apply", str(patch_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return worktree

    def run_for_task(self, task_id: str) -> dict[str, Any]:
        catalog = _mutants_catalog()
        if task_id not in catalog:
            return {
                "task_id": task_id,
                "status": "SKIPPED",
                "reason": "No mutation definitions registered",
                "mutants": [],
            }

        task_dir = self.tasks_dir / task_id
        patch_path = task_dir / "solution" / "feature.patch"
        test_files = list((task_dir / "tests").glob("test_feature_*.py"))
        if not patch_path.exists() or not test_files:
            return {
                "task_id": task_id,
                "status": "SKIPPED",
                "reason": "Missing feature.patch or feature test file",
                "mutants": [],
            }
        feature_test = test_files[0]

        worktree = self._prepare_patched_worktree(patch_path)
        local_test_path = worktree / "tests" / feature_test.name
        shutil.copy2(feature_test, local_test_path)
        rel_test = f"tests/{feature_test.name}"
        mutants_results: list[dict[str, Any]] = []
        t0 = time.perf_counter()

        try:
            for m in catalog[task_id]:
                target_file = worktree / m["file"]
                orig_text = target_file.read_text(encoding="utf-8")
                if m["target"] not in orig_text:
                    mutants_results.append(
                        {
                            "id": m["id"],
                            "file": m["file"],
                            "description": m["description"],
                            "status": "SKIPPED",
                            "killed": False,
                            "reason": "Target snippet not found in patched file",
                        }
                    )
                    continue

                mutated_text = orig_text.replace(m["target"], m["replacement"], 1)
                target_file.write_text(mutated_text, encoding="utf-8")

                env = dict(os.environ)
                env["PYTHONPATH"] = str((worktree / "src").resolve())
                env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
                mt0 = time.perf_counter()
                proc = subprocess.run(
                    [sys.executable, "-m", "pytest", rel_test, "-x", "-q", "--tb=line"],
                    cwd=str(worktree),
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                )
                # Restore original patched text immediately
                target_file.write_text(orig_text, encoding="utf-8")

                killed = proc.returncode != 0
                mutants_results.append(
                    {
                        "id": m["id"],
                        "file": m["file"],
                        "description": m["description"],
                        "status": "KILLED" if killed else "SURVIVED",
                        "killed": killed,
                        "pytest_returncode": proc.returncode,
                        "duration_sec": round(time.perf_counter() - mt0, 2),
                        "pytest_summary": (proc.stdout or proc.stderr).strip().splitlines()[-1]
                        if (proc.stdout or proc.stderr).strip()
                        else "",
                    }
                )
        finally:
            shutil.rmtree(worktree, ignore_errors=True)

        evaluated = [r for r in mutants_results if r["status"] in {"KILLED", "SURVIVED"}]
        killed_count = sum(1 for r in evaluated if r["killed"])
        survived_count = len(evaluated) - killed_count
        score = round((killed_count / len(evaluated) * 100.0), 1) if evaluated else 0.0

        return {
            "task_id": task_id,
            "status": "PASSED" if evaluated and survived_count == 0 else "WARN",
            "total_mutants": len(evaluated),
            "killed": killed_count,
            "survived": survived_count,
            "mutation_score_pct": score,
            "duration_sec": round(time.perf_counter() - t0, 2),
            "mutants": mutants_results,
        }

    def run_all(self, task_ids: list[str] | None = None, save: bool = True) -> dict[str, Any]:
        ensure_directories()
        t0 = time.perf_counter()
        ids = task_ids or sorted(p.name for p in self.tasks_dir.iterdir() if p.is_dir())
        results = [self.run_for_task(tid) for tid in ids]
        total_mutants = sum(r.get("total_mutants", 0) for r in results)
        total_killed = sum(r.get("killed", 0) for r in results)
        overall_score = round((total_killed / total_mutants * 100.0), 1) if total_mutants else 0.0

        report = {
            "total_tasks": len(results),
            "total_mutants": total_mutants,
            "total_killed": total_killed,
            "total_survived": total_mutants - total_killed,
            "overall_mutation_score_pct": overall_score,
            "duration_sec": round(time.perf_counter() - t0, 2),
            "tasks": results,
        }
        if save:
            MUTATION_REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

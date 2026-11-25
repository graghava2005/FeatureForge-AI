"""Module A: Automated Repository Analyzer for pallets/click."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from config.settings import (
    BASE_COMMIT_SHA,
    REPO_ANALYSIS_PATH,
    TARGET_REPO_DIR,
    TARGET_REPO_NAME,
    ensure_directories,
)


@dataclass
class ModuleSummary:
    relative_path: str
    line_count: int
    classes: list[dict[str, Any]]
    functions: list[str]
    imports: list[str]


class RepositoryAnalyzer:
    """Inspects repository structure, source AST, tests, and Git history."""

    def __init__(self, repo_dir: Path = TARGET_REPO_DIR) -> None:
        self.repo_dir = Path(repo_dir)

    def _run_git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", "-C", str(self.repo_dir), *args],
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc.stdout.strip()

    def verify_clean_base_commit(self, expected_sha: str = BASE_COMMIT_SHA) -> dict[str, Any]:
        if not self.repo_dir.exists():
            raise FileNotFoundError(f"Repository directory does not exist: {self.repo_dir}")

        head_sha = self._run_git("rev-parse", "HEAD")
        if len(head_sha) != 40:
            raise ValueError(f"Expected 40-char SHA, got {head_sha!r}")

        status_out = self._run_git("status", "--porcelain")
        is_clean = len(status_out.strip()) == 0
        branch = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        commit_subject = self._run_git("log", "-1", "--format=%s")
        commit_date = self._run_git("log", "-1", "--format=%cI")

        return {
            "head_sha": head_sha,
            "matches_expected_base_commit": head_sha == expected_sha,
            "expected_base_commit": expected_sha,
            "is_clean_working_tree": is_clean,
            "dirty_files": status_out.splitlines() if status_out else [],
            "branch": branch,
            "commit_subject": commit_subject,
            "commit_date": commit_date,
        }

    def get_git_history(self, limit: int = 30) -> list[dict[str, str]]:
        raw = self._run_git(
            "log",
            f"-n{limit}",
            "--format=%H|%cI|%an|%s",
        )
        commits: list[dict[str, str]] = []
        for line in raw.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                commits.append(
                    {
                        "sha": parts[0],
                        "date": parts[1],
                        "author": parts[2],
                        "subject": parts[3],
                    }
                )
        return commits

    def _parse_python_module(self, py_path: Path) -> ModuleSummary:
        source = py_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(py_path))
        classes: list[dict[str, Any]] = []
        functions: list[str] = []
        imports: list[str] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods: list[str] = []
                init_params: list[str] = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(item.name)
                        if item.name == "__init__":
                            init_params = [
                                a.arg
                                for a in item.args.args + item.args.kwonlyargs
                                if a.arg != "self"
                            ]
                classes.append(
                    {
                        "name": node.name,
                        "methods": methods,
                        "init_params": init_params,
                        "bases": [ast.unparse(b) for b in node.bases],
                    }
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)

        return ModuleSummary(
            relative_path=py_path.relative_to(self.repo_dir).as_posix(),
            line_count=len(source.splitlines()),
            classes=classes,
            functions=functions,
            imports=sorted(set(imports)),
        )

    def analyze_source_tree(self) -> dict[str, Any]:
        src_dir = self.repo_dir / "src" / "click"
        modules: list[dict[str, Any]] = []
        all_symbols: dict[str, list[str]] = {}
        init_exports: list[str] = []

        for py_file in sorted(src_dir.glob("*.py")):
            summary = self._parse_python_module(py_file)
            modules.append(asdict(summary))
            rel = summary.relative_path
            all_symbols[rel] = [c["name"] for c in summary.classes] + summary.functions
            if py_file.name == "__init__.py":
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source)
                for node in tree.body:
                    if isinstance(node, ast.ImportFrom):
                        for alias in node.names:
                            init_exports.append(alias.asname or alias.name)

        top_level_dirs = sorted(
            p.name for p in self.repo_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
        )
        top_level_files = sorted(
            p.name for p in self.repo_dir.iterdir() if p.is_file()
        )

        return {
            "top_level_dirs": top_level_dirs,
            "top_level_files": top_level_files,
            "source_module_count": len(modules),
            "total_source_lines": sum(m["line_count"] for m in modules),
            "modules": modules,
            "public_exports": sorted(set(init_exports)),
            "symbol_index": all_symbols,
        }

    def analyze_test_suite(self) -> dict[str, Any]:
        tests_dir = self.repo_dir / "tests"
        test_files: list[dict[str, Any]] = []
        total_test_functions = 0

        for py_file in sorted(tests_dir.rglob("*.py")):
            if py_file.name == "conftest.py":
                continue
            source = py_file.read_text(encoding="utf-8", errors="replace")
            try:
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError:
                continue
            test_names: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    test_names.append(node.name)
            total_test_functions += len(test_names)
            test_files.append(
                {
                    "relative_path": py_file.relative_to(self.repo_dir).as_posix(),
                    "test_count": len(test_names),
                    "sample_tests": test_names[:8],
                }
            )

        return {
            "test_file_count": len(test_files),
            "total_test_functions": total_test_functions,
            "test_files": test_files,
        }

    def scan_existing_capabilities(
        self, source_analysis: dict[str, Any], git_history: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Programmatically verify which candidate capabilities already exist vs are absent."""
        src_texts = {
            p.relative_to(self.repo_dir).as_posix(): p.read_text(encoding="utf-8", errors="replace")
            for p in sorted((self.repo_dir / "src" / "click").glob("*.py"))
        }
        combined_src = "\n".join(src_texts.values())
        history_text = "\n".join(c["subject"] for c in git_history)

        probes = [
            {
                "id": "deprecated_flag",
                "title": "Command and Parameter deprecation warnings",
                "probe_patterns": [r"deprecated:\s*bool\s*\|\s*str", r"DeprecationWarning: The command"],
                "check_symbols": ["deprecated"],
            },
            {
                "id": "auto_envvar",
                "title": "Automatic environment variable prefix lookup",
                "probe_patterns": [r"auto_envvar_prefix", r"allow_from_autoenv"],
                "check_symbols": ["auto_envvar_prefix"],
            },
            {
                "id": "option_constraints",
                "title": "Option Mutual Exclusivity and Dependency Constraints (conflicts_with / requires)",
                "probe_patterns": [r"\bconflicts_with\b", r"\bmutually_exclusive\b", r"\brequires\s*:"],
                "check_symbols": ["conflicts_with", "requires"],
            },
            {
                "id": "command_aliases",
                "title": "Command and Subcommand Aliases in Group Dispatch and Help",
                "probe_patterns": [r"\baliases\s*:\s*", r"resolve_alias", r"_command_aliases"],
                "check_symbols": ["aliases"],
            },
            {
                "id": "bytesize_type",
                "title": "Human-Readable ByteSize Parameter Type",
                "probe_patterns": [r"class\s+ByteSize\b", r"\bBYTE_SIZE\b"],
                "check_symbols": ["ByteSize"],
            },
            {
                "id": "no_color_force_color",
                "title": "Standard NO_COLOR and FORCE_COLOR Environment Variable Resolution",
                "probe_patterns": [r"\bNO_COLOR\b", r"\bFORCE_COLOR\b"],
                "check_symbols": ["NO_COLOR", "FORCE_COLOR"],
            },
            {
                "id": "echo_table",
                "title": "Terminal Table Formatter and Printer (click.echo_table)",
                "probe_patterns": [r"def\s+echo_table\b", r"def\s+format_table\b"],
                "check_symbols": ["echo_table"],
            },
        ]

        # Extract all init params across classes for strict AST verification
        init_param_index: dict[str, list[str]] = {}
        for mod in source_analysis["modules"]:
            for cls in mod["classes"]:
                init_param_index[f"{mod['relative_path']}::{cls['name']}"] = cls["init_params"]

        existing_rejected: list[dict[str, Any]] = []
        novel_opportunities: list[dict[str, Any]] = []

        for probe in probes:
            matched_evidence: list[str] = []
            for pat in probe["probe_patterns"]:
                for rel_path, text in src_texts.items():
                    if re.search(pat, text):
                        matched_evidence.append(f"Pattern `{pat}` matched in `{rel_path}`")
                if re.search(pat, history_text, re.IGNORECASE):
                    matched_evidence.append(f"Pattern `{pat}` matched in git history")

            for sym in probe["check_symbols"]:
                for cls_key, params in init_param_index.items():
                    if sym in params:
                        matched_evidence.append(f"AST init param `{sym}` found in `{cls_key}`")
                if sym in source_analysis["public_exports"]:
                    matched_evidence.append(f"Public export `{sym}` found in `src/click/__init__.py`")

            entry = {
                "id": probe["id"],
                "title": probe["title"],
                "already_exists": bool(matched_evidence),
                "evidence": sorted(set(matched_evidence)),
            }
            if matched_evidence:
                existing_rejected.append(entry)
            else:
                novel_opportunities.append(entry)

        return {
            "existing_capabilities_rejected": existing_rejected,
            "novel_feature_opportunities": novel_opportunities,
        }

    def run(self, save: bool = True) -> dict[str, Any]:
        ensure_directories()
        t0 = time.perf_counter()
        git_state = self.verify_clean_base_commit()
        git_history = self.get_git_history(limit=30)
        source_analysis = self.analyze_source_tree()
        test_analysis = self.analyze_test_suite()
        opportunities = self.scan_existing_capabilities(source_analysis, git_history)
        elapsed = round(time.perf_counter() - t0, 3)

        report = {
            "repository": TARGET_REPO_NAME,
            "repo_path": str(self.repo_dir),
            "git_verification": git_state,
            "git_recent_commits": git_history[:15],
            "source_analysis": source_analysis,
            "test_analysis": test_analysis,
            "capability_scan": opportunities,
            "analysis_duration_sec": elapsed,
        }

        if save:
            REPO_ANALYSIS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

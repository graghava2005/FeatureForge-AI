"""Module C: Novelty and Specification Auditor."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from config.settings import TARGET_REPO_DIR

REQUIRED_PROPOSAL_FIELDS = [
    "feature_title",
    "problem_description",
    "user_requirements",
    "expected_behaviour",
    "acceptance_criteria",
    "technical_implementation_approach",
    "new_feature_test_scenarios",
    "regression_test_requirements",
]

AMBIGUOUS_PATTERNS = [
    r"\bTBD\b",
    r"\bTODO\b",
    r"\bfixme\b",
    r"\bmaybe\b",
    r"\bsomehow\b",
    r"\bappropriately\b",
    r"\betc\.?\b",
    r"\band so on\b",
]


class NoveltyChecker:
    """Validates feature proposals against actual repository source, tests, and git history."""

    def __init__(self, repo_dir: Path = TARGET_REPO_DIR) -> None:
        self.repo_dir = Path(repo_dir)
        self._src_cache: dict[str, str] | None = None
        self._init_params_cache: dict[str, set[str]] | None = None
        self._exports_cache: set[str] | None = None

    def _load_repo_index(self) -> None:
        if self._src_cache is not None:
            return
        src_dir = self.repo_dir / "src" / "click"
        self._src_cache = {}
        self._init_params_cache = {}
        self._exports_cache = set()

        for py_file in sorted(src_dir.glob("*.py")):
            rel = py_file.relative_to(self.repo_dir).as_posix()
            text = py_file.read_text(encoding="utf-8", errors="replace")
            self._src_cache[rel] = text
            tree = ast.parse(text, filename=str(py_file))
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                            self._init_params_cache[f"{rel}::{node.name}"] = {
                                a.arg for a in item.args.args + item.args.kwonlyargs if a.arg != "self"
                            }
                elif py_file.name == "__init__.py" and isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        self._exports_cache.add(alias.asname or alias.name)

    def check_existing_functionality(self, proposal: dict[str, Any]) -> dict[str, Any]:
        self._load_repo_index()
        assert self._src_cache is not None
        assert self._init_params_cache is not None
        assert self._exports_cache is not None

        evidence: list[str] = []
        for symbol in proposal.get("probe_symbols", []):
            for cls_key, params in self._init_params_cache.items():
                if symbol in params:
                    evidence.append(f"Symbol '{symbol}' already exists as __init__ parameter in {cls_key}")
            if symbol in self._exports_cache:
                evidence.append(f"Symbol '{symbol}' already exported in src/click/__init__.py")
            for rel, content in self._src_cache.items():
                if re.search(rf"\b(def|class)\s+{re.escape(symbol)}\b", content):
                    evidence.append(f"Definition of '{symbol}' already exists in {rel}")
                if re.search(rf"\b{re.escape(symbol)}\s*:\s*", content):
                    evidence.append(f"Typed attribute/param '{symbol}' already exists in {rel}")

        return {
            "passed": len(evidence) == 0,
            "already_exists": len(evidence) > 0,
            "evidence": sorted(set(evidence)),
        }

    def check_completeness(self, proposal: dict[str, Any]) -> dict[str, Any]:
        missing: list[str] = []
        for field in REQUIRED_PROPOSAL_FIELDS:
            val = proposal.get(field)
            if not val or (isinstance(val, list) and len(val) == 0):
                missing.append(field)
        return {"passed": len(missing) == 0, "missing_fields": missing}

    def check_ambiguity(self, proposal: dict[str, Any]) -> dict[str, Any]:
        text_parts = [
            str(proposal.get("feature_title", "")),
            str(proposal.get("problem_description", "")),
            str(proposal.get("expected_behaviour", "")),
            " ".join(proposal.get("user_requirements", [])),
            " ".join(proposal.get("acceptance_criteria", [])),
        ]
        blob = "\n".join(text_parts)
        hits: list[str] = []
        for pat in AMBIGUOUS_PATTERNS:
            for match in re.findall(pat, blob, flags=re.IGNORECASE):
                hits.append(match)
        return {"passed": len(hits) == 0, "ambiguous_terms": sorted(set(hits))}

    def check_ac_and_test_alignment(self, proposal: dict[str, Any]) -> dict[str, Any]:
        acs = proposal.get("acceptance_criteria", [])
        scenarios = proposal.get("new_feature_test_scenarios", [])
        reg_reqs = proposal.get("regression_test_requirements", [])
        issues: list[str] = []
        if len(acs) < 4:
            issues.append(f"Expected >=4 acceptance criteria, got {len(acs)}")
        if len(scenarios) < 4:
            issues.append(f"Expected >=4 test scenarios, got {len(scenarios)}")
        if not reg_reqs:
            issues.append("Missing regression test requirements")
        return {
            "passed": len(issues) == 0,
            "ac_count": len(acs),
            "scenario_count": len(scenarios),
            "issues": issues,
        }

    def audit_candidates(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        """Audit all candidates: reject existing/duplicate/incomplete ones, approve 5 distinct tasks."""
        approved: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        audit_records: list[dict[str, Any]] = []

        for cand in candidates:
            existing_res = self.check_existing_functionality(cand)
            completeness_res = self.check_completeness(cand)
            ambiguity_res = self.check_ambiguity(cand)
            alignment_res = self.check_ac_and_test_alignment(cand)

            # Duplicate check against already-approved proposals
            max_sim = 0.0
            similar_to = None
            cand_text = (
                f"{cand.get('feature_title', '')} {cand.get('subsystem', '')} "
                f"{' '.join(cand.get('user_requirements', []))}"
            )
            for prev in approved:
                prev_text = (
                    f"{prev.get('feature_title', '')} {prev.get('subsystem', '')} "
                    f"{' '.join(prev.get('user_requirements', []))}"
                )
                sim = fuzz.token_set_ratio(cand_text, prev_text)
                if sim > max_sim:
                    max_sim = sim
                    similar_to = prev.get("task_id")

            duplicate_ok = max_sim < 75.0 and cand.get("subsystem") not in {
                p.get("subsystem") for p in approved
            }
            is_valid = (
                existing_res["passed"]
                and completeness_res["passed"]
                and ambiguity_res["passed"]
                and alignment_res["passed"]
                and duplicate_ok
            )

            reasons: list[str] = []
            if not existing_res["passed"]:
                reasons.append("Feature already exists in base commit: " + "; ".join(existing_res["evidence"]))
            if not completeness_res["passed"]:
                reasons.append("Missing fields: " + ", ".join(completeness_res["missing_fields"]))
            if not ambiguity_res["passed"]:
                reasons.append("Ambiguous phrasing detected: " + ", ".join(ambiguity_res["ambiguous_terms"]))
            if not alignment_res["passed"]:
                reasons.extend(alignment_res["issues"])
            if not duplicate_ok:
                reasons.append(f"Too similar to {similar_to} (similarity={max_sim:.1f}%) or duplicate subsystem")

            record = {
                "task_id": cand.get("task_id"),
                "slug": cand.get("slug"),
                "feature_title": cand.get("feature_title"),
                "status": "APPROVED" if is_valid else "REJECTED",
                "checks": {
                    "novelty_against_repo": existing_res,
                    "completeness": completeness_res,
                    "non_ambiguous": ambiguity_res,
                    "ac_test_alignment": alignment_res,
                    "duplicate_check": {
                        "passed": duplicate_ok,
                        "max_similarity_pct": round(max_sim, 2),
                        "most_similar_task": similar_to,
                    },
                },
                "rejection_reasons": reasons,
            }
            audit_records.append(record)

            if is_valid and len(approved) < 5:
                approved.append(cand)
            else:
                rejected.append(record)

        return {
            "total_evaluated": len(candidates),
            "approved_count": len(approved),
            "rejected_count": len(rejected),
            "approved_proposals": approved,
            "rejected_proposals": rejected,
            "audit_records": audit_records,
        }

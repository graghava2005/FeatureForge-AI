"""Central settings for FeatureForge AI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = (
    PROJECT_ROOT.parent
    if PROJECT_ROOT.name == "source" and (PROJECT_ROOT.parent / "tasks").exists()
    else PROJECT_ROOT
)
REPOS_DIR = DATA_ROOT / "repos"
TARGET_REPO_NAME = "pallets/click"
TARGET_REPO_URL = "https://github.com/pallets/click.git"
TARGET_REPO_DIR = REPOS_DIR / "click"
BASE_COMMIT_SHA = "08b803cf32ceb2ae6a772c62d5da42757a897d44"

TASKS_DIR = DATA_ROOT / "tasks"
OUTPUT_DIR = (
    DATA_ROOT / "evidence"
    if DATA_ROOT != PROJECT_ROOT and (DATA_ROOT / "evidence").exists()
    else DATA_ROOT / "output"
)
HARBOR_JOBS_DIR = OUTPUT_DIR / "harbor_jobs"

REPO_ANALYSIS_PATH = OUTPUT_DIR / "repository_analysis.json"
GENERATED_TASKS_PATH = OUTPUT_DIR / "generated_tasks.json"
QUALITY_REPORT_PATH = OUTPUT_DIR / "quality_report.json"
MUTATION_REPORT_PATH = OUTPUT_DIR / "mutation_report.json"
BENCHMARK_RESULTS_PATH = OUTPUT_DIR / "benchmark_results.json"
FINAL_REPORT_PATH = (
    DATA_ROOT / "FINAL_VERIFICATION_REPORT.md"
    if DATA_ROOT != PROJECT_ROOT
    else OUTPUT_DIR / "FINAL_VERIFICATION_REPORT.md"
)

PYTHON_EXE = Path(sys.executable)
HARBOR_EXE_DEFAULT = PYTHON_EXE.parent / "Scripts" / "harbor.exe"
if not HARBOR_EXE_DEFAULT.exists():
    HARBOR_EXE_DEFAULT = PYTHON_EXE.parent / "harbor"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DEFAULT_LLM_MODEL = os.environ.get("FEATUREFORGE_MODEL", "gpt-4o-mini")
HARBOR_VERSION_PREFIX = "0.25"

DESIGN_COLORS = {
    "background": "#FFFFFF",
    "primary_text": "#171717",
    "secondary_text": "#666666",
    "primary_orange": "#F97316",
    "light_orange": "#FFF7ED",
    "border": "#E5E7EB",
    "success": "#15803D",
    "success_bg": "#F0FDF4",
    "error": "#B91C1C",
    "error_bg": "#FEF2F2",
    "warning": "#B45309",
    "warning_bg": "#FFFBEB",
}


def ensure_directories() -> None:
    """Ensure required workspace directories exist."""
    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    HARBOR_JOBS_DIR.mkdir(parents=True, exist_ok=True)

"""Setup script: clones pallets/click if missing, checks base commit, and verifies baseline pytest."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import BASE_COMMIT_SHA, TARGET_REPO_DIR, TARGET_REPO_URL, ensure_directories


def main() -> int:
    ensure_directories()

    if not TARGET_REPO_DIR.exists():
        print(f"Cloning {TARGET_REPO_URL} into {TARGET_REPO_DIR}...")
        subprocess.run(["git", "clone", TARGET_REPO_URL, str(TARGET_REPO_DIR)], check=True)

    subprocess.run(
        ["git", "-C", str(TARGET_REPO_DIR), "checkout", BASE_COMMIT_SHA],
        check=True,
    )
    head = subprocess.run(
        ["git", "-C", str(TARGET_REPO_DIR), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    print(f"Verified base commit: {head}")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(TARGET_REPO_DIR / "src")
    print("Running baseline pallets/click pytest suite...")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short"],
        cwd=str(TARGET_REPO_DIR),
        env=env,
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

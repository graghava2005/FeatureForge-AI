#!/usr/bin/env bash
set -uo pipefail

APP_DIR="${APP_DIR:-/app}"
TESTS_DIR="${TESTS_DIR:-/tests}"
VERIFIER_DIR="${VERIFIER_DIR:-/logs/verifier}"
PYTHON_BIN="${PYTHON_BIN:-python}"

mkdir -p "$VERIFIER_DIR"
cd "$APP_DIR"

export PYTHONPATH="$APP_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON_BIN" - "$APP_DIR" "$TESTS_DIR" "$VERIFIER_DIR" "test_feature_command_aliases.py" <<'PY'
import json
import os
import pathlib
import shutil
import subprocess
import sys

app_dir = pathlib.Path(sys.argv[1])
tests_dir = pathlib.Path(sys.argv[2])
verifier_dir = pathlib.Path(sys.argv[3])
feature_test_file = tests_dir / sys.argv[4]
pass_to_pass_file = tests_dir / "pass_to_pass.json"

regression_targets = json.loads(pass_to_pass_file.read_text(encoding="utf-8"))

local_feat = app_dir / "tests" / feature_test_file.name
shutil.copy2(feature_test_file, local_feat)
env = dict(os.environ)
env["PYTHONPATH"] = str((app_dir / "src").resolve())
env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

try:
    feat_proc = subprocess.run(
        [sys.executable, "-m", "pytest", f"tests/{feature_test_file.name}", "-v", "--tb=short"],
        cwd=str(app_dir),
        env=env,
        capture_output=True,
        text=True,
    )
finally:
    local_feat.unlink(missing_ok=True)
print("=== FEATURE TESTS ===")
print(feat_proc.stdout)
if feat_proc.stderr:
    print(feat_proc.stderr, file=sys.stderr)

reg_proc = subprocess.run(
    [sys.executable, "-m", "pytest", *regression_targets, "-q", "--tb=short"],
    cwd=str(app_dir),
    env=env,
    capture_output=True,
    text=True,
)
print("=== REGRESSION TESTS ===")
print(reg_proc.stdout)
if reg_proc.stderr:
    print(reg_proc.stderr, file=sys.stderr)

reward = 1.0 if (feat_proc.returncode == 0 and reg_proc.returncode == 0) else 0.0

(verifier_dir / "reward.txt").write_text(
    "1\n" if reward == 1.0 else "0\n", encoding="utf-8"
)
(verifier_dir / "reward.json").write_text(
    json.dumps({"reward": reward}, indent=2), encoding="utf-8"
)
(verifier_dir / "verifier_details.json").write_text(
    json.dumps(
        {
            "feature_returncode": feat_proc.returncode,
            "regression_returncode": reg_proc.returncode,
            "reward": reward,
            "feature_test_file": sys.argv[4],
            "regression_targets": regression_targets,
        },
        indent=2,
    ),
    encoding="utf-8",
)
sys.exit(0 if reward == 1.0 else 1)
PY

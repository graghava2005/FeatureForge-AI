#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
SOLUTION_DIR="${SOLUTION_DIR:-/solution}"

cd "$APP_DIR"
git -c safe.directory="*" apply --check "$SOLUTION_DIR/feature.patch"
git -c safe.directory="*" apply "$SOLUTION_DIR/feature.patch"
echo "Applied reference feature patch cleanly."

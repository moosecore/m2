#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/moose/projects/m2/repo"
cd "$REPO_DIR"

echo "[deploy] pulling latest..."
git pull --ff-only

echo "[deploy] done"

#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for OpenGero.
# Runs the no-Docker local dev path from the repo root: FastAPI + RDKit API and
# the Vite web client. SQLite is used so docking jobs run inline (no Redis/worker
# needed); AutoDock Vina is optional and the API falls back to a labeled heuristic.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# System packages: python venv support and the shared libraries RDKit's wheel
# links against. Kept here (not in application code) so the base image stays stock.
sudo apt-get update -qq
sudo apt-get install -y -qq --no-install-recommends \
  python3.12-venv libxrender1 libxext6 libsm6

# Python API environment.
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r apps/api/requirements.txt

# Web client dependencies.
(cd apps/web && npm install)

echo "OpenGero install complete."

#!/usr/bin/env bash
# Brings up the full OpenGero stack (postgres, redis, api, worker, web) via
# docker compose, in the foreground so all service logs stream into this
# terminal. `--build` picks up the currently checked-out source.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "[stack] waiting for the Docker daemon..."
for _ in $(seq 1 180); do
  sudo docker info >/dev/null 2>&1 && break
  sleep 1
done
sudo docker info >/dev/null 2>&1 || { echo "[stack] Docker daemon not available"; exit 1; }

echo "[stack] building and starting OpenGero (web http://localhost:8080, api http://localhost:8000)"
exec sudo docker compose up --build

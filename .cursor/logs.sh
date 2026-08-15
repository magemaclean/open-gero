#!/usr/bin/env bash
# Streams logs for the whole OpenGero compose stack in a persistent terminal.
# The stack is brought up by .cursor/start.sh; this waits for it, then follows.
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

echo "[logs] waiting for the Docker daemon and stack..."
for _ in $(seq 1 240); do
  sudo docker compose ps >/dev/null 2>&1 && break
  sleep 1
done

exec sudo docker compose logs -f

#!/usr/bin/env bash
# Per-boot startup for the Docker-first OpenGero environment.
# Ensures the Docker daemon is running (configured for this nested VM) and brings
# the full compose stack up in the background, then returns. Idempotent: safe to
# run on every boot and to re-run.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

DOCKERD_LOG=/var/log/opengero-dockerd.log

# Nested-VM networking: same-bridge (container<->container) traffic is L2, but
# bridge-nf would push it through the dropping iptables FORWARD chain.
sudo sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null 2>&1 || true
sudo sysctl -w net.bridge.bridge-nf-call-ip6tables=0 >/dev/null 2>&1 || true

# Start dockerd if it isn't already up. setsid detaches it into its own session
# so it survives this script returning; root owns the log file.
if ! sudo docker info >/dev/null 2>&1; then
  echo "[start] launching Docker daemon"
  sudo rm -f /var/run/docker.pid
  sudo bash -c "setsid dockerd >'$DOCKERD_LOG' 2>&1 < /dev/null &"
  for _ in $(seq 1 90); do
    sudo docker info >/dev/null 2>&1 && break
    sleep 1
  done
fi
sudo docker info >/dev/null 2>&1 || {
  echo "[start] Docker daemon failed to start"; sudo tail -n 40 "$DOCKERD_LOG" 2>/dev/null || true; exit 1;
}

# Bring up the stack. Images are pre-built during install; --build picks up any
# source changes in the checked-out branch (cached layers keep this fast).
echo "[start] starting OpenGero stack (web http://localhost:8080, api http://localhost:8000)"
sudo docker compose up -d --build
sudo docker compose ps

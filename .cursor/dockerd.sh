#!/usr/bin/env bash
# Per-boot Docker daemon for the OpenGero Cloud Agent environment.
# Runs in a dedicated terminal so its logs stay visible and it can be restarted.
set -uo pipefail

# Nested-VM networking/storage prerequisites (idempotent).
sudo sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null 2>&1 || true
sudo sysctl -w net.bridge.bridge-nf-call-ip6tables=0 >/dev/null 2>&1 || true

# If a daemon is already up (e.g. started during install on a just-in-time VM),
# don't start a second one — just follow its log.
if sudo docker info >/dev/null 2>&1; then
  echo "[dockerd] Docker daemon already running; streaming /tmp/dockerd.log"
  exec sudo tail -n +1 -F /tmp/dockerd.log
fi

sudo rm -f /var/run/docker.pid
echo "[dockerd] starting Docker daemon"
exec sudo dockerd

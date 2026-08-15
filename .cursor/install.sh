#!/usr/bin/env bash
# Docker-first Cloud Agent bootstrap for OpenGero.
# Installs Docker Engine + Compose, configures the daemon for this nested VM,
# and pre-builds the Compose images so they are baked into the environment
# snapshot. The full stack (postgres, redis, api, worker, web) then runs via
# `docker compose` from the dockerd/stack terminals defined in environment.json.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

export DEBIAN_FRONTEND=noninteractive

# 1. Docker Engine + Compose plus the packages a nested (container-in-container)
#    VM needs: iptables for NAT/port publishing, fuse-overlayfs for the storage
#    driver (overlay2 cannot stack on the VM's own overlay rootfs), uidmap.
# --force-confold/--force-confdef keep existing conffiles without an interactive
# prompt (the base image ships /etc/fuse.conf, which otherwise stalls fuse3).
sudo apt-get update -qq
sudo apt-get install -y -qq --no-install-recommends \
  -o Dpkg::Options::=--force-confold -o Dpkg::Options::=--force-confdef \
  docker.io docker-compose-v2 iptables fuse-overlayfs uidmap

# 2. Daemon config for the nested VM: use the classic graphdriver with
#    fuse-overlayfs (the containerd snapshotter's overlayfs cannot mount the
#    multi-layer images here).
sudo mkdir -p /etc/docker
printf '%s\n' '{"features":{"containerd-snapshotter":false},"storage-driver":"fuse-overlayfs"}' \
  | sudo tee /etc/docker/daemon.json >/dev/null

# 3. Allow the agent user to talk to the Docker socket without sudo in new shells.
sudo groupadd -f docker
sudo usermod -aG docker "$(id -un)" || true

# 4. Bridge fix for this VM: same-network container-to-container traffic is L2,
#    but bridge-nf pushes it through the (dropping) iptables FORWARD chain.
sudo sysctl -w net.bridge.bridge-nf-call-iptables=0 >/dev/null 2>&1 || true
sudo sysctl -w net.bridge.bridge-nf-call-ip6tables=0 >/dev/null 2>&1 || true

# 5. Start the daemon just long enough to pre-build the Compose images so a fresh
#    agent boots fast. dockerd itself is a per-boot process (started by the
#    dockerd terminal); only the built images persist in the snapshot.
if ! sudo docker info >/dev/null 2>&1; then
  sudo rm -f /var/run/docker.pid
  sudo bash -c 'setsid dockerd >/var/log/opengero-dockerd.log 2>&1 < /dev/null &'
  for _ in $(seq 1 60); do
    sudo docker info >/dev/null 2>&1 && break
    sleep 1
  done
fi
sudo docker info >/dev/null 2>&1 || { echo "dockerd failed to start"; sudo tail -n 40 /var/log/opengero-dockerd.log 2>/dev/null || true; exit 1; }

sudo docker compose build

echo "OpenGero docker install complete."

#!/usr/bin/env bash
# Prepare a fresh Amazon Linux 2023 EC2 instance: Docker, Compose, and swap
# (swap is essential on a 1 GB free-tier box for both building and running).
#   curl -fsSL <raw-url>/bootstrap.sh | bash      # or: bash bootstrap.sh
set -euo pipefail

echo "==> Installing Docker + git"
sudo dnf -y install docker git
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"

echo "==> Installing Docker Compose plugin"
ARCH="$(uname -m)"
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${ARCH}" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

echo "==> Creating 4 GB swap (if absent)"
if [ ! -f /swapfile ]; then
  sudo fallocate -l 4G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

echo
echo "==> Done. Log out and back in (or run 'newgrp docker') so the docker group applies."
echo "    Then: cd TravelOS/deploy/aws-free-tier && cp .env.example .env && \$EDITOR .env && docker compose up -d --build"

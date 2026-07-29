#!/usr/bin/env bash
# Vol Diagnostics — Server Deploy Script
# Run on the Oracle Cloud instance after SSH.
# Installs Docker, clones the repo, and launches the stack.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/AdamMooo/vol-diagnostics/main/scripts/deploy.sh | bash
#   OR
#   bash scripts/deploy.sh
#
# NOTE: also open ports 80/443/8501 in the OCI Console Security List
# (Networking -> VCN -> public subnet -> Default Security List -> Add
# Ingress Rules) — iptables alone is not enough, both layers block traffic.

set -euo pipefail

echo "=== Vol Diagnostics Deploy ==="
echo "Target: Ubuntu 24.04 (ARM64)"
echo ""

# 1. Install Docker (Ubuntu)
if ! command -v docker &> /dev/null; then
    echo "[1/5] Installing Docker..."
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker "$USER"
    echo "  Docker installed. You may need to log out/in for group to apply."
    echo "  Re-run this script after logging back in if 'docker ps' fails."
else
    echo "[1/5] Docker already installed: $(docker --version)"
fi

# 2. Open firewall ports (iptables — Ubuntu on OCI has no firewalld)
echo "[2/5] Opening firewall ports (80, 443, 8501)..."
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8501 -j ACCEPT 2>/dev/null || true
sudo apt-get install -y iptables-persistent 2>/dev/null || true
sudo netfilter-persistent save 2>/dev/null || true
echo "  Ports opened locally. Also open them in OCI Security List via console (see note above)."

# 3. Clone repo (or pull if already cloned)
REPO_DIR="$HOME/vol-diagnostics"
if [ -d "$REPO_DIR/.git" ]; then
    echo "[3/5] Repo exists — pulling latest..."
    cd "$REPO_DIR"
    git pull
else
    echo "[3/5] Cloning repo..."
    git clone https://github.com/AdamMooo/vol-diagnostics.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

# 4. Setup .env
if [ ! -f .env ]; then
    echo "[4/5] Creating .env from template — EDIT THIS before compose up!"
    cp .env.example .env
    echo ""
    echo "  ⚠️  EDIT .env with your SMTP credentials:"
    echo "     nano $REPO_DIR/.env"
    echo ""
else
    echo "[4/5] .env already exists."
fi

# 5. Create out/ directory for bind mount
mkdir -p out/surface_history out/vol_index out/vol-report out/oi_history out/monitor

# 6. Build and launch
echo "[5/5] Building and launching (this takes 3-5 min on first run)..."
docker compose up -d --build

echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Status:"
docker compose ps
echo ""
echo "Next steps:"
echo "  1. Edit .env if you haven't:  nano $REPO_DIR/.env"
echo "  2. Migrate parquet data from Windows (see scripts/migrate-data.ps1)"
echo "  3. Verify dashboard: http://$(curl -s ifconfig.me):80"
echo "  4. Check scheduler: docker compose logs scheduler"
echo "  5. Open OCI Security List ports 80/443 if not done"

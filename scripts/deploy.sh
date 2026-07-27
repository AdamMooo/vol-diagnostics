#!/usr/bin/env bash
# Vol Diagnostics — Server Deploy Script
# Run on the Oracle Cloud instance after SSH.
# Installs Docker, clones the repo, and launches the stack.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/AdamMooo/vol-diagnostics/main/scripts/deploy.sh | bash
#   OR
#   bash scripts/deploy.sh

set -euo pipefail

echo "=== Vol Diagnostics Deploy ==="
echo "Target: Oracle Linux 8 (ARM64)"
echo ""

# 1. Install Docker (Oracle Linux 8 / CentOS stream)
if ! command -v docker &> /dev/null; then
    echo "[1/5] Installing Docker..."
    sudo dnf install -y dnf-utils
    sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker "$USER"
    echo "  Docker installed. You may need to log out/in for group to apply."
    echo "  Re-run this script after logging back in if 'docker ps' fails."
else
    echo "[1/5] Docker already installed: $(docker --version)"
fi

# 2. Open firewall ports
echo "[2/5] Opening firewall ports (80, 443, 8501)..."
sudo firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
sudo firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
sudo firewall-cmd --permanent --add-port=8501/tcp 2>/dev/null || true
sudo firewall-cmd --reload 2>/dev/null || true
echo "  Ports opened (also open in OCI Security List via console)."

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
mkdir -p out/surface_history out/vol_index out/vol-report

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

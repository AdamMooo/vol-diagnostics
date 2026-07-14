# Oracle Cloud Free Tier — Vol Diagnostics Setup Guide

Created: 2026-06-24
Updated: 2026-06-25

## What's Free (Always Free Tier — never expires)

| Resource | Free Allowance |
|----------|---------------|
| ARM Compute (VM.Standard.A1.Flex) | 2 OCPUs + 12 GB RAM |
| Boot volume storage | 200 GB total (across all instances) |
| Public IP | 1 reserved public IP |
| Bandwidth | 10 Mbps |
| Object Storage | 20 GB |

---

## Step 1: Create Instance — Image and Shape

Navigate to: **Compute → Instances → Create Instance**

### Instance Name & Placement

| Field | Set To |
|-------|--------|
| **Name** | `vol-diagnostics` |
| **Compartment** | root (default) |
| **Availability domain** | leave default |

### Image (Operating System)

| Field | Value |
|-------|-------|
| **Operating system** | Canonical Ubuntu 24.04 Minimal aarch64 |
| **Image build** | latest available (e.g. 2026.04.30-1) |

- Click **Change image** if not already showing Ubuntu
- Select **Canonical Ubuntu** → **24.04 Minimal** → **aarch64**
- This is the minimal ARM64 Ubuntu — lightweight, familiar commands (`apt`, `systemctl`)
- Default SSH user will be `ubuntu` (not `opc` like Oracle Linux)

### Shape (THIS IS THE KEY PART)

| Field | Value |
|-------|-------|
| **Shape** | VM.Standard.A1.Flex |
| **Shape build** | Virtual machine, 2 core OCPU, 12 GB memory, 2 Gbps network bandwidth |
| **Always Free-eligible** | ✅ Yes |

How to set:
1. Click **Change shape**
2. Select the **Ampere** tab (NOT AMD, NOT Intel)
3. Choose **VM.Standard.A1.Flex**
4. Set **Number of OCPUs:** `2`
5. Set **Amount of memory (GB):** `12`
6. These are the maximums for Always Free

> ⚠️ If you see VM.Standard.E2.1.Micro selected — that's the tiny AMD instance (1 OCPU, 1 GB RAM). Not what we want. Make sure you're on the Ampere tab.

---

## Step 2: Security

### Shielded Instances / Confidential Computing

**Skip this entirely.** Leave defaults as-is.

- These are enterprise security features (Secure Boot, TPM, memory encryption)
- They add complexity without benefit for our Docker/Streamlit use case
- The warning about confidential computing being incompatible is fine — we don't need it

### SSH Keys

| Field | Value |
|-------|-------|
| **Key type** | Generate a key pair for me |

Steps:
1. Select **"Generate a key pair for me"**
2. Oracle will create the key pair
3. **⚠️ CRITICAL: Click "Download the private key" immediately**
4. Save the `.key` file somewhere safe:
   - Recommended: `C:\Users\AdamMorris\.ssh\vol-diagnostics.key`
   - Backup: OneDrive, password manager, or USB
5. You can also download the public key for your records
6. **If you lose the private key, you are permanently locked out of the instance**

You'll use this key later to connect:
```powershell
ssh -i "C:\Users\AdamMorris\.ssh\vol-diagnostics.key" ubuntu@YOUR_PUBLIC_IP
```

---

## Step 3: Networking

### Primary VNIC

| Field | Value |
|-------|-------|
| **VNIC name** | leave default |
| **Virtual cloud network** | Create new virtual cloud network (or use existing) |
| **VCN name** | `gamma-vcn` (auto-generated name is fine too) |
| **Subnet** | Create new **public** subnet |
| **Subnet name** | `gamma-subnet` (auto-generated is fine) |

### Private IPv4 Address

| Field | Value |
|-------|-------|
| **Assignment** | ✅ Automatically assign private IPv4 address |

Leave as default — Oracle assigns the next unused address.

### Public IPv4 Address — ⚠️ CRITICAL

| Field | Value |
|-------|-------|
| **Assignment** | ✅ **Automatically assign public IPv4 address** — MUST BE CHECKED |

> ⚠️ **This is the most important checkbox on this page.** Without a public IP:
> - You cannot SSH into the instance
> - The dashboard is not accessible from the internet
> - You'd have to set up a bastion host or VPN (unnecessary complexity)
>
> The checkbox requires a **public subnet** — make sure your subnet is public, not private.

### IPv6 Address

| Field | Value |
|-------|-------|
| **Assign IPv6** | Leave unchecked (not needed) |

### Advanced Options (Networking)

Skip — leave all defaults.

---

## Step 4: Storage (Boot Volume)

| Field | Value |
|-------|-------|
| **Boot volume size** | `50 GB` (minimum — this is free) |
| **Boot volume performance** | **Balanced** (default is fine) |
| **Encrypt using...** | Oracle-managed encryption (default) |
| **In-transit encryption** | Unchecked (default) |

### Why a cost estimate might show up

The Oracle cost estimator sometimes shows ~$2.62/month because it includes block storage at list price. **You will NOT actually be charged** as long as:
- Total boot volume ≤ 200 GB (you're using 50 GB — well within)
- You're on the Always Free shape (VM.Standard.A1.Flex)

The Always Free block storage quota (200 GB) zeroes out the cost. The estimator just isn't smart enough to show that.

> **Bottom line:** Ignore any cost estimate. It will show $0.00 on your actual bill.

---

## Step 5: Review & Create

Before clicking Create, verify:

| Check | Expected Value |
|-------|---------------|
| **Image** | Canonical Ubuntu 24.04 Minimal aarch64 |
| **Shape** | VM.Standard.A1.Flex, 2 OCPU, 12 GB |
| **Always Free** | ✅ Eligible |
| **Boot volume** | 50 GB |
| **Public IP** | ✅ Assigned |
| **SSH key** | ✅ Downloaded private key |

Click **Create**.

The instance takes 1–3 minutes to provision. Status: Provisioning → Running.

---

## Step 5b: When the console says "Out of host capacity" (the common case)

Toronto's Always-Free A1 shape is chronically capacity-constrained — the console
Create button just fails. The fix is to retry the **launch API** on a loop until a
host frees up. Use `scripts/oracle-retry.ps1` (in this repo) instead of clicking.

One-time setup:
```powershell
# 1. install OCI CLI
Invoke-Expression ((Invoke-WebRequest https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.ps1 -UseBasicParsing).Content)
# (reopen PowerShell so PATH refreshes, then `oci --version` should print 3.x)

# 2. authenticate (1-hour browser session token — fine while you're at the machine)
oci session authenticate            # pick region: ca-toronto-1
```

The script's CONFIG block is already filled with this tenancy's OCIDs (compartment,
public subnet, Ubuntu 24.04 aarch64 image, the single Toronto AD) and points at
`~/.ssh/vol-diagnostics.pub`. Run it:
```powershell
cd C:\dev\vol-diagnostics
.\scripts\oracle-retry.ps1
```

It prints a `... no capacity` line every 60s and stops the moment a host accepts
(green **SUCCESS**), or stops with a red **ERROR** on any non-capacity problem.
Notes:
- Keep the PowerShell window open and the machine awake — closing it kills the loop.
- The session token expires after ~1h. Either re-run `oci session authenticate`
  when you sit back down, or switch to a permanent API key (`oci setup config` +
  add the public key under your user → API Keys) and drop the `--auth security_token`
  flag from the script for unattended overnight runs.
- Boot-volume minimum is **50 GB** (47 was rejected — `InvalidParameter`).

---

## Recovery: setting this up from a different computer

The VM runs independently of any laptop — once it exists, returning/wiping the
machine you provisioned from costs nothing. To re-establish control from a fresh
computer you need exactly three things:

1. **The SSH private key** (`vol-diagnostics.key`) — the one irreplaceable secret. Keep a
   copy off this machine (personal drive / password manager). Lose it = locked out.
2. **The repo** — `git clone` the private GitHub repo (read access + a PAT/deploy key).
3. **The server's public IP** — write it down once the instance is running.

Day-to-day management needs only SSH + the IP:
```powershell
ssh -i "<path>\vol-diagnostics.key" ubuntu@YOUR_PUBLIC_IP
```
The OCI CLI is only needed to *provision or manage the instance itself* — not for
deploying or operating the stack. Re-deriving the public key from the private key
if you ever need it again: `ssh-keygen -y -f vol-diagnostics.key > vol-diagnostics.pub`.

---

## After Instance is Running

### 1. Get your public IP

1. Go to **Compute → Instances → vol-diagnostics**
2. Wait for status to show **Running** (green)
3. Copy the **Public IP address** from the instance details (e.g. `129.xx.xx.xx`)
4. Save this IP — you'll need it for SSH, deploy, and accessing the dashboard

### 2. SSH in (first time)

```powershell
# From Windows PowerShell or Terminal
ssh -i "C:\Users\AdamMorris\.ssh\vol-diagnostics.key" ubuntu@YOUR_PUBLIC_IP
```

Notes:
- Default user for Ubuntu images is `ubuntu` (not `opc`)
- First connection will ask to accept the host fingerprint — type `yes`
- If you get a "permissions too open" error on the key file:
  ```powershell
  icacls "C:\Users\AdamMorris\.ssh\vol-diagnostics.key" /inheritance:r /grant:r "$env:USERNAME:(R)"
  ```

### 3. Open firewall ports (TWO places)

Oracle blocks traffic by default in TWO layers. You must open ports in BOTH.

#### 3a. Oracle Cloud Console — Security List (web UI)

1. Go to **Networking → Virtual Cloud Networks** in Oracle Console
2. Click on your VCN (e.g. `gamma-vcn`)
3. Click on your **public subnet**
4. Click on the **Default Security List**
5. Click **Add Ingress Rules**
6. Add these rules one at a time:

| Source CIDR | IP Protocol | Dest Port Range | Description |
|-------------|-------------|-----------------|-------------|
| `0.0.0.0/0` | TCP | `80` | HTTP (Caddy) |
| `0.0.0.0/0` | TCP | `443` | HTTPS (Caddy + Let's Encrypt) |
| `0.0.0.0/0` | TCP | `8501` | Streamlit direct (optional backup) |

> Note: Port 22 (SSH) should already be open by default in the security list.

#### 3b. Instance firewall — iptables (via SSH)

Ubuntu on Oracle Cloud has iptables rules that ALSO block traffic. After SSH in:

```bash
# Open ports 80, 443, 8501
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8501 -j ACCEPT

# Save the rules so they persist across reboots
sudo apt-get update && sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

> ⚠️ If you skip either layer (console security list OR instance iptables), traffic will still be blocked.

### 4. Install Docker

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker prerequisites
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository (for Ubuntu 24.04 noble)
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine + Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add yourself to the docker group (avoids needing sudo)
sudo usermod -aG docker $USER

# IMPORTANT: Log out and back in for group change to take effect
exit
```

SSH back in and verify:
```bash
ssh -i "C:\Users\AdamMorris\.ssh\vol-diagnostics.key" ubuntu@YOUR_PUBLIC_IP

docker --version
# Expected: Docker version 27.x.x or similar

docker compose version
# Expected: Docker Compose version v2.x.x

# Quick test
docker run hello-world
```

### 5. Clone and Deploy

```bash
# Clone the repo
git clone https://github.com/AdamMooo/vol-diagnostics.git
cd vol-diagnostics

# Create out/ directories for data
mkdir -p out/surface_history out/vol_index out/gex

# Create .env from template
cp .env.example .env
nano .env
```

Fill in `.env`:
```env
# Email recipients (comma-separated)
GEX_EMAIL_TO=your-email@example.com

# SMTP settings (Gmail app password recommended)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM=your-email@gmail.com

# Streamlit password (optional)
PASSWORD=your-dashboard-password

# Domain (leave empty for IP-only access)
DOMAIN=
```

Then build and launch:
```bash
# Build and start all services (first build takes 3-5 min on ARM)
docker compose up -d --build

# Check status — all 3 services should show "Up"
docker compose ps

# Check logs
docker compose logs dashboard    # Streamlit startup
docker compose logs scheduler    # Cron scheduler
docker compose logs caddy        # Reverse proxy
```

### 6. Verify Everything Works

| Test | Command / URL | Expected |
|------|---------------|----------|
| Dashboard via Caddy | `http://YOUR_PUBLIC_IP` | Streamlit dashboard loads |
| Dashboard direct | `http://YOUR_PUBLIC_IP:8501` | Streamlit dashboard loads |
| Health check | `docker compose exec dashboard python -m engine.health_check` | Reports status |
| Scheduler running | `docker compose logs scheduler` | Shows "supercronic" started |
| Caddy running | `docker compose logs caddy` | Shows reverse proxy active |

### 7. Migrate Existing Parquet Data

From your Windows machine:
```powershell
# Transfer all historical parquet data to the server
scp -i "C:\Users\AdamMorris\.ssh\vol-diagnostics.key" -r C:\dev\vol-diagnostics\out\* ubuntu@YOUR_PUBLIC_IP:~/vol-diagnostics/out/
```

Then on the server, restart to pick up the data:
```bash
cd ~/vol-diagnostics
docker compose restart

# Verify data loaded
docker compose exec dashboard python -m engine.health_check
```

The health check should report all tickers as OK with the latest snapshot date.

### 8. Ongoing Maintenance

| Task | Command |
|------|---------|
| Pull latest code + rebuild | `cd ~/vol-diagnostics && bash scripts/update.sh` |
| View scheduler logs | `docker compose logs --tail=50 scheduler` |
| Check health | `docker compose exec dashboard python -m engine.health_check` |
| Force a manual daily run | `docker compose exec scheduler python -m engine.run_daily --send --force` |
| Restart everything | `docker compose restart` |
| Stop everything | `docker compose down` |
| Start everything | `docker compose up -d` |
| View resource usage | `docker stats` |

---

## Idle Instance Reclamation Warning

Oracle reclaims Always Free instances that are idle for 7+ days. All three conditions must be true simultaneously:
- CPU utilization < 20% at 95th percentile
- Network utilization < 20%
- Memory utilization < 20%

**Our stack naturally avoids this because:**
- Streamlit dashboard keeps memory allocated (~500MB+)
- Docker healthchecks ping the dashboard every 30 seconds (CPU/network activity)
- Scheduler runs daily data collection (CPU spike weekdays)

If you want extra safety, the crontab already includes a health check that runs daily and generates network/CPU activity.

---

## Troubleshooting

### Can't SSH in
- Verify the instance status is **Running** in the console
- Check that port 22 is in the security list ingress rules (should be by default)
- Verify you're using `ubuntu@` not `opc@` (Ubuntu images use `ubuntu`)
- Check key file permissions: `icacls "key.key" /inheritance:r /grant:r "$env:USERNAME:(R)"`

### Dashboard not accessible from browser
- Check BOTH firewall layers (security list + iptables)
- Verify Caddy is running: `docker compose logs caddy`
- Try direct Streamlit port: `http://YOUR_PUBLIC_IP:8501`
- Run: `docker compose ps` — all services should show "Up"

### Docker build fails on ARM
- ARM builds can be slow (~5 min first time) — be patient
- If pip install fails, ensure `gcc g++` are in the Dockerfile (they are)
- Try: `docker compose build --no-cache`

### Email not sending
- Check `.env` SMTP settings
- Verify GEX_SEND=1 is set in docker-compose.yml for scheduler (it is)
- Check logs: `docker compose logs scheduler`
- Gmail requires an "App Password" (not your regular password)

### Instance stopped/reclaimed
- Check Oracle Console for instance status
- If reclaimed, create a new instance and redeploy
- Your data is safe on the boot volume unless you terminated the instance

---

## Cost Summary

| Item | Cost |
|------|------|
| VM.Standard.A1.Flex (2 OCPU, 12 GB) | $0.00 |
| Boot volume (50 GB) | $0.00 (within 200 GB free) |
| Public IP | $0.00 |
| Outbound bandwidth (10 TB/mo) | $0.00 |
| **Monthly total** | **$0.00** |

> The Always Free tier never expires. As long as you stay within these limits, Oracle will not charge you.

---
---
<!-- LINKS:AUTO -->
## Related
**Project:** [[_planning/vol-diagnostics/ROADMAP|ROADMAP]] · [[_planning/vol-diagnostics/STATE|STATE]] · [[vol-diagnostics/vol-diagnostics|Hub]]
<!-- LINKS:END -->

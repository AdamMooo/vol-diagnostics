# Oracle Cloud Free Tier — Gamma OMM Setup Guide

Created: 2026-06-24

## What's Free (Always Free Tier — never expires)

| Resource | Free Allowance |
|----------|---------------|
| ARM Compute (VM.Standard.A1.Flex) | 2 OCPUs + 12 GB RAM |
| Boot volume storage | 200 GB total (across all instances) |
| Public IP | 1 reserved public IP |
| Bandwidth | 10 Mbps |
| Object Storage | 20 GB |

---

## Step 1: Basic Info

| Field | Set To |
|-------|--------|
| **Name** | `gamma-omm` |
| **Compartment** | root (default) |
| **Availability domain** | leave default |

### Image

- Click **Change image** if not already set
- Select **Oracle Linux 8** (aarch64) or **Ubuntu 22.04 Minimal (aarch64)**
- Ubuntu is fine for Docker — either works

### Shape (THIS IS THE KEY PART)

- Click **Change shape**
- Select the **Ampere** tab (NOT AMD, NOT Intel)
- Choose **VM.Standard.A1.Flex**
- Set:
  - **Number of OCPUs:** `2`
  - **Amount of memory (GB):** `12`
- These are the maximums for Always Free

> ⚠️ If you see VM.Standard.E2.1.Micro selected — that's the tiny AMD instance (1 OCPU, 1 GB RAM). Not what we want.

---

## Step 2: Security

### SSH Key

- Select **Generate a key pair for me**
- Oracle will create the key pair and prompt you to **download the private key (.key file)**
- **SAVE THIS FILE SOMEWHERE SAFE** — OneDrive, password manager, USB — NOT just on this laptop
- You can also download the public key for your records
- If you ever lose the private key, you're locked out of the instance

When you SSH in later, point to wherever you saved the .key file:
```powershell
ssh -i "C:\path\to\your\saved\ssh-key.key" opc@YOUR_PUBLIC_IP
```

---

## Step 3: Networking

| Field | Set To |
|-------|--------|
| **Virtual cloud network** | Create new VCN (or use existing if one was auto-created) |
| **VCN name** | `gamma-vcn` (if creating new) |
| **Subnet** | Create new **public subnet** |
| **Subnet name** | `gamma-subnet` (if creating new) |
| **Public IPv4 address** | ✅ **Assign a public IPv4 address** — CHECK THIS BOX |

> ⚠️ If you skip the public IP, you cannot SSH in or access the dashboard from the internet.

---

## Step 4: Storage (Boot Volume)

**THIS IS WHERE THE $2.62 COMES FROM**

| Field | Set To |
|-------|--------|
| **Boot volume size** | `47 GB` (minimum — this is free) |
| **Boot volume performance** | **Lower Cost** or **Balanced** — either is free |
| **Encrypt using...** | Leave as Oracle-managed encryption (default) |
| **In-transit encryption** | Unchecked (default) |

### Why $2.62 shows up

The $2.62 estimate appears because Oracle's cost estimator includes all block storage at list price. **You will NOT actually be charged** as long as:
- Total boot volume ≤ 200 GB (you're using 47 GB — well within)
- You're on the Always Free shape (VM.Standard.A1.Flex)

The Always Free block storage quota (200 GB) zeroes out the cost. The estimator just isn't smart enough to show that.

> **Bottom line:** Ignore the $2.62 estimate. It will show $0.00 on your actual bill.

---

## Step 5: Review & Create

- Verify shape says **VM.Standard.A1.Flex, 2 OCPU, 12 GB**
- Verify boot volume is **47 GB**
- Verify public IP is assigned
- Click **Create**

The instance takes 1–3 minutes to provision. Status will go: Provisioning → Running.

---

## After Instance is Running

### 1. Get your public IP

- Go to **Compute → Instances → gamma-omm**
- Copy the **Public IP address** (e.g. `129.xx.xx.xx`)

### 2. SSH in

```powershell
ssh -i "C:\path\to\your\saved\ssh-key.key" opc@YOUR_PUBLIC_IP
```

(`opc` is the default user for Oracle Linux; use `ubuntu` if you chose Ubuntu)

### 3. Open firewall ports (Oracle security list)

Oracle blocks ports 80/443/8501 by default. You must open them:

**In the Oracle Console:**
1. Go to **Networking → Virtual Cloud Networks → gamma-vcn**
2. Click on your **public subnet**
3. Click on the **Default Security List**
4. Click **Add Ingress Rules**
5. Add these rules:

| Source CIDR | Protocol | Dest Port | Description |
|-------------|----------|-----------|-------------|
| `0.0.0.0/0` | TCP | `80` | HTTP |
| `0.0.0.0/0` | TCP | `443` | HTTPS |
| `0.0.0.0/0` | TCP | `8501` | Streamlit (optional, Caddy handles it) |

**On the instance itself (iptables):**

Oracle Linux has iptables rules that also block traffic. After SSH in:

```bash
# Oracle Linux
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=8501/tcp
sudo firewall-cmd --reload

# Ubuntu (if you chose Ubuntu)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8501 -j ACCEPT
sudo netfilter-persistent save
```

### 4. Install Docker

```bash
# Oracle Linux 8
sudo dnf install -y dnf-utils
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Log out and back in for group to take effect
exit
```

Then SSH back in and verify:
```bash
docker --version
docker compose version
```

### 5. Clone and Deploy

```bash
git clone https://github.com/AdamMooo/gamma-omm.git
cd gamma-omm

# Create .env from template
cp .env.example .env
nano .env   # fill in SMTP credentials, email recipients

# Build and launch
docker compose up -d --build

# Check status
docker compose ps
docker compose logs dashboard
```

### 6. Verify

- Dashboard: `http://YOUR_PUBLIC_IP` (Caddy proxies to Streamlit)
- Direct Streamlit: `http://YOUR_PUBLIC_IP:8501`
- Scheduler logs: `docker compose logs scheduler`

### 7. Migrate Existing Parquet Data

From your Windows machine:
```powershell
scp -i "C:\path\to\your\saved\ssh-key.key" -r C:\dev\gamma-omm\out\* opc@YOUR_PUBLIC_IP:~/gamma-omm/out/
```

Then on the server, copy into the Docker volume:
```bash
docker compose down
docker compose up -d
# The volume mount maps host out/ if using bind mount,
# or you may need: docker cp ~/gamma-omm/out/. gamma-dashboard:/app/out/
```

---

## Idle Instance Reclamation Warning

Oracle reclaims Always Free instances that are idle for 7 days (all three must be true):
- CPU < 20% at 95th percentile
- Network < 20%
- Memory < 20%

**Our stack avoids this** — Streamlit keeps the instance alive with periodic health checks and the scheduler runs daily. If you want extra safety, add a lightweight cron that pings the dashboard every few minutes.

---

## Cost Summary

| Item | Cost |
|------|------|
| VM.Standard.A1.Flex (2 OCPU, 12 GB) | $0.00 |
| Boot volume (47 GB) | $0.00 (within 200 GB free) |
| Public IP | $0.00 |
| Outbound bandwidth (10 TB/mo) | $0.00 |
| **Monthly total** | **$0.00** |

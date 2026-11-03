# SSH & Terminal Command Guide — Vol Diagnostics

Complete reference for running commands in your terminal, SSH deployment, and the dev/prod workflow cycle.

---

## Table of Contents

1. [Quick Start: Running Commands](#quick-start)
2. [SSH Setup & Key Management](#ssh-setup)
3. [Deployment Workflow](#deployment-workflow)
4. [Verification & Monitoring](#verification--monitoring)
5. [Debugging & Troubleshooting](#debugging--troubleshooting)
6. [Command Reference](#command-reference)

---

## Quick Start

### Running Python Commands Locally

**Assumption:** You've already run `.venv` activation (the `.bashrc` does this automatically, so no `source .venv/bin/activate` needed).

```bash
# Local dev dashboard — opens in browser
cd ~/dev/vol-diagnostics
streamlit run app.py

# Single-ticker CLI (prints to stdout, saves PNGs to out/)
python -m engine.run_gex --ticker SPY

# All three tickers + email HTML (saves to out/, no send)
python -m engine.run_daily --dry-run

# Run tests
pytest engine/tests -v

# Health check (shows current data freshness)
python -m engine.health_check
python -m engine.health_check --strict  # exit code 1 if any ticker is stale
python -m engine.health_check --json    # machine-readable output
```

### Running Commands on the Oracle Server

All remote commands follow this pattern:

```bash
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "COMMAND_HERE"
```

**Examples:**

```bash
# Pull latest code and rebuild
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && git pull && docker compose up -d --build"

# Check if the site is running
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "docker ps"

# Tail the container logs (Ctrl+C to exit)
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "docker logs -f vol-diagnostics-app-1"

# Quick health check on the server
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && python -m engine.health_check"
```

**Windows equivalent** (PowerShell):

```powershell
# Same commands, just swap the quoting
ssh -i "$env:USERPROFILE\.ssh\vol-diagnostics.key" ubuntu@40.233.113.63 'cd ~/vol-diagnostics && git pull && docker compose up -d --build'
```

---

## SSH Setup & Key Management

### First-Time Setup

**Your private key must live on your machine only.** It was generated once and is stored in KeePassXC.

```bash
# 1. Create .ssh directory if it doesn't exist
mkdir -p ~/.ssh

# 2. Restore the private key from KeePassXC vault
#    Open KeePassXC → vol-diagnostics-secrets.kdbx → master passphrase
#    Find "vol-diagnostics SSH key" → Advanced → Attachments → Save
#    Save it to: ~/.ssh/vol-diagnostics.key

# 3. Fix permissions (CRITICAL — SSH refuses keys with mode 0644 or 0777)
chmod 600 ~/.ssh/vol-diagnostics.key

# 4. Verify it works
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "echo 'SSH works!'"
```

### Key Permissions (Why They Matter)

SSH is paranoid about private key permissions. This is a security feature — if your key is readable by other users on your machine, SSH treats it as compromised.

```bash
# GOOD ✓
ls -la ~/.ssh/vol-diagnostics.key
# Output: -rw------- 1 adam adam 3434 Aug 16 14:22 vol-diagnostics.key
#         └─ 600 = only owner can read/write ✓

# BAD ✗ — SSH will refuse to use this
-rw-r--r-- 1 adam adam 3434 Aug 16 14:22 vol-diagnostics.key
#  └─ 644 = world-readable (SECURITY RISK)

# FIX
chmod 600 ~/.ssh/vol-diagnostics.key
```

### Recovering a Corrupt/Lost Key

If your key is lost or the passphrase is forgotten:

**Option 1: Restore from vault (normal path)**
```bash
# Open KeePassXC, find the SSH key attachment, save it again
# Then: chmod 600 ~/.ssh/vol-diagnostics.key
```

**Option 2: Generate a new key pair (nuclear option)**
```bash
# On your machine
ssh-keygen -t ed25519 -f ~/.ssh/vol-diagnostics.key -N ""

# Extract the public key (you'll need this for the server)
ssh-keygen -y -f ~/.ssh/vol-diagnostics.key > ~/.ssh/vol-diagnostics.pub

# Add the .pub to the Oracle console:
#   OCI Console → Compute → Instances → vol-diagnostics
#   → Instance details → Console connections → Add SSH Key
#   → Paste contents of ~/.ssh/vol-diagnostics.pub

# Update GitHub secret:
#   GitHub repo → Settings → Secrets and variables → Repository secrets
#   → ORACLE_SSH_KEY → update with new private key

# Update KeePassXC vault for next time
```

### SSH Config (Optional — Shorthand)

Create `~/.ssh/config` to avoid typing the full command:

```
Host oracle-vol
    HostName 40.233.113.63
    User ubuntu
    IdentityFile ~/.ssh/vol-diagnostics.key
    StrictHostKeyChecking accept-new
```

Then you can run:

```bash
ssh oracle-vol "cd ~/vol-diagnostics && git pull"
# Instead of:
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && git pull"
```

---

## Deployment Workflow

### Standard Deploy Cycle

**Goal:** Push local changes to production (Oracle).

#### Step 1: Commit Locally

```bash
cd ~/dev/vol-diagnostics

# See what changed
git status
git diff

# Stage and commit (follows Conventional Commits format)
git add engine/health_check.py
git commit -m "fix: align health_check cutoff to session.py (16:35 ET)"

# Check it's on the right branch
git branch        # should be main or a feature branch
git log --oneline -5
```

#### Step 2: Push to GitHub

```bash
# Push to your fork or main (depending on your workflow)
git push origin main
# OR for a feature branch:
git push origin my-feature-branch
```

#### Step 3: Deploy to Oracle

**IMPORTANT:** Never background this command. Watch it in the foreground.

```bash
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && git pull && docker compose up -d --build"
```

**What this does:**
1. SSH into the Oracle VM
2. Enter the project directory
3. Pull the latest code from GitHub
4. Rebuild the Docker image (this takes 1–2 minutes)
5. Start the container in the background (`-d`)

**Output you'll see:**

```
ubuntu@oracle-vm:~/vol-diagnostics$ git pull
remote: Enumerating objects...
...
 engine/health_check.py | 12 +++++++-----
...
Fast-forward
 1 file changed, 12 insertions(+), 5 deletions(-)

ubuntu@oracle-vm:~/vol-diagnostics$ docker compose up -d --build
Building app
Step 1/8 : FROM python:3.11-slim
 ---> a1b2c3d4e5f6
Step 2/8 : WORKDIR /app
 ...
Step 8/8 : EXPOSE 8501
 ---> Using cache
 ---> a1b2c3d4e5f6
Successfully built a1b2c3d4e5f6
Successfully tagged vol-diagnostics-app:latest

Creating vol-diagnostics-app-1 ... done
```

#### Step 4: Verify the Deploy

After the build finishes, check that the new code is running:

```bash
bash scripts/verify-deploy.sh
```

**What it does:** Compares three SHAs:
- `origin/main` — what's on GitHub
- Server's repo HEAD — what the server has
- Running container's stamp — what the container was built from

**Output:**

```
Comparing SHAs:
  Local origin/main:   abc123def456
  Server repo HEAD:    abc123def456
  Container GIT_SHA:   abc123def456
✓ All three match — deploy is live.
```

**If they don't match:**

```
✗ MISMATCH:
  - Server repo is behind origin/main (git pull may have failed)
  - Container is behind server repo (docker compose up may have failed)
Fix: Re-run the deploy command, watch for errors.
```

#### Step 5: Visit the Site

```
https://40.233.113.63.nip.io
```

(Replace the IP with your Oracle instance IP if different.)

---

## Verification & Monitoring

### Real-Time Logs

```bash
# Follow container logs (Ctrl+C to stop)
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "docker logs -f vol-diagnostics-app-1"

# Last 50 lines (no follow)
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "docker logs -n 50 vol-diagnostics-app-1"

# Logs from last 10 minutes
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "docker logs --since 10m vol-diagnostics-app-1"
```

### Container Status

```bash
# Check if container is running
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "docker ps"

# Check all containers (including stopped ones)
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "docker ps -a"

# Inspect container details
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "docker inspect vol-diagnostics-app-1"
```

### Health Checks

```bash
# From your local machine (no SSH needed)
python -m engine.health_check

# From the server
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && python -m engine.health_check --strict"

# Full history scan (finds gaps in accumulated data)
python -m engine.health_check --json | jq '.full_history'
```

### Data Freshness

```bash
# Check the latest data date stored locally
python3 << 'EOF'
import pandas as pd
df = pd.read_parquet('out/gex_snapshots.parquet')
print(f"Latest data: {df['date'].max()}")
EOF

# From the server
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 << 'EOF'
cd ~/vol-diagnostics
python3 -c "import pandas as pd; df = pd.read_parquet('out/gex_snapshots.parquet'); print(f'Latest: {df[\"date\"].max()}')"
EOF
```

---

## Debugging & Troubleshooting

### "Permission Denied" When Connecting

```bash
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "echo ok"
# Error: Permission denied (publickey)
```

**Fixes:**

```bash
# 1. Check key permissions (must be 0600)
ls -la ~/.ssh/vol-diagnostics.key
chmod 600 ~/.ssh/vol-diagnostics.key

# 2. Check if the key file exists
test -f ~/.ssh/vol-diagnostics.key && echo "Key found" || echo "Key missing"

# 3. Try verbose SSH to see what's happening
ssh -v -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "echo ok"
# Look for "Trying private key" lines — if your key is listed, it tried it

# 4. Verify the public key is on the server (if you regenerated it)
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cat ~/.ssh/authorized_keys"
```

### Container Won't Start

```bash
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "docker compose logs app"
# Look for Python errors, dependency issues, or port conflicts
```

**Common causes:**

```bash
# Missing .env file
# → Fix: Copy .env to the server, or regenerate secrets

# Port 8501 already in use
# → Fix: docker ps, kill the old container, restart

# Out of disk space
# → Fix: docker image prune, docker volume prune

# Bad git state (merge conflict after git pull)
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && git status"
# If there's a conflict, you may need to reset: git reset --hard origin/main
```

### GitHub Workflow Failures

Workflows run in `.github/workflows/` and are triggered on schedule or manual dispatch.

```bash
# Check latest workflow run
# → GitHub repo → Actions tab
# → Click the failing workflow

# Or via gh CLI
gh run list --workflow=daily-report.yml -L 5
gh run view RUN_ID --log

# Manually trigger the daily collection
gh workflow run daily-report.yml -f force=true

# Check data freshness in Actions
gh workflow run data-freshness-check.yml
```

### Data Not Collecting (Stale for >1 Session)

**Diagnosis:**

```bash
# 1. Is the GitHub workflow running?
gh run list --workflow=daily-report.yml -L 5
# Look for recent runs (should have one per day on trading days)

# 2. Did it succeed or fail?
gh run view LAST_RUN_ID
# Status: success / failure / cancelled

# 3. Is the data in Object Storage?
python -m engine.health_check
# Shows if data is current or stale

# 4. Can the workflow connect to OCI?
# Check the workflow logs in GitHub Actions → Daily Data Collection → latest run
# Look for "Restore history from Object Storage" step
```

**Recovery:**

```bash
# Force a re-collection on the next scheduled run
gh workflow run daily-report.yml

# Or trigger manually with --force
gh workflow run daily-report.yml -f force=true

# If local data is good but server is stale
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 << 'EOF'
cd ~/vol-diagnostics
python -m engine.restore_from_oci \
  --bucket vol-diagnostics-backup --region ca-toronto-1 --dest ./out --force
EOF
```

---

## Command Reference

### Frequently Used Commands

| Command | What It Does | When to Use |
|---------|-----------|-----------|
| `streamlit run app.py` | Open the dashboard locally | Testing UI changes |
| `python -m engine.run_gex --ticker SPY` | Collect and analyze one ticker | Spot-checking specific data |
| `pytest engine/tests -v` | Run the test suite | Before committing |
| `git push origin main` | Push to GitHub | After committing locally |
| `ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && git pull && docker compose up -d --build"` | Deploy to production | After pushing to GitHub |
| `bash scripts/verify-deploy.sh` | Check that deploy succeeded | After deployment |
| `python -m engine.health_check` | Check data freshness locally | Monitoring data pipeline |
| `ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "docker logs -f vol-diagnostics-app-1"` | Follow container logs | Debugging server issues |
| `gh workflow run daily-report.yml` | Force data collection | Triggering backfill |

### SSH Aliases (Add to ~/.bash_aliases or ~/.bashrc)

```bash
# Add these lines to ~/.bash_aliases, then restart your terminal
# source ~/.bashrc

alias ssh-oracle='ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63'
alias oracle-logs='ssh-oracle "docker logs -f vol-diagnostics-app-1"'
alias oracle-health='ssh-oracle "cd ~/vol-diagnostics && python -m engine.health_check"'
alias oracle-pull='ssh-oracle "cd ~/vol-diagnostics && git pull"'
```

Then you can run:

```bash
ssh-oracle "docker ps"
oracle-logs
oracle-health
```

### Batch Operations

**Deploy to prod + verify:**

```bash
git push origin main && \
ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && git pull && docker compose up -d --build" && \
sleep 5 && \
bash scripts/verify-deploy.sh
```

**Collect data locally + run tests:**

```bash
python -m engine.run_gex --ticker SPY && pytest engine/tests -v
```

**Check all three tickers on server:**

```bash
for ticker in SPY QQQ IWM; do
  ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "cd ~/vol-diagnostics && python -m engine.run_gex --ticker $ticker"
done
```

---

## Troubleshooting SSH Hangs

If `ssh` hangs without responding:

```bash
# Press Ctrl+C
# Then try with a timeout
timeout 10 ssh -i ~/.ssh/vol-diagnostics.key ubuntu@40.233.113.63 "echo ok"

# If timeout is reached, the server is unreachable. Possible causes:
# - Oracle instance is down (check OCI console)
# - Network connectivity issue
# - SSH port is blocked (unlikely if it's working elsewhere)

# Force a reboot via OCI console if the instance is stuck
# (DO NOT use SSH, since SSH is what's hung)
```

---

## Additional Resources

- `.CLAUDE.md` — Project rules and constraints
- `.planning/STATE.md` — Current phase and priority
- `scripts/verify-deploy.sh` — Deployment verification script
- `docker-compose.yml` — Container configuration
- `Dockerfile` — Image build definition

---

**Last Updated:** 2026-09-11  
**Status:** Complete and tested

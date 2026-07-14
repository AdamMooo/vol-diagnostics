# Vol Diagnostics — Migrate parquet data to Oracle Cloud
# Run from your local Windows machine after the remote instance is deployed.
# For the reverse direction (pull current data down FROM Oracle), see
# scripts/sync-from-oracle.ps1 — Oracle's disk is the actual source of truth
# since the daily collection job moved to GitHub Actions on 2026-07-14; this
# script is now mainly useful for one-off local backfills, not routine syncing.
#
# Usage:
#   .\scripts\migrate-data.ps1 -IP "129.xx.xx.xx" -KeyFile "C:\path\to\ssh-key.key"
#
# What it does:
#   1. Copies all out/ parquet files to the server via scp
#   2. Restarts containers to pick up the data
#   3. Runs health-check to verify

param(
    [Parameter(Mandatory=$true)]
    [string]$IP,

    [Parameter(Mandatory=$true)]
    [string]$KeyFile,

    [string]$User = "ubuntu",
    [string]$RemoteDir = "~/vol-diagnostics/out"
)

$ErrorActionPreference = "Stop"
$LocalOut = Join-Path $PSScriptRoot "..\out"

if (-not (Test-Path $LocalOut)) {
    Write-Error "Local out/ directory not found at $LocalOut"
    exit 1
}

if (-not (Test-Path $KeyFile)) {
    Write-Error "SSH key file not found: $KeyFile"
    exit 1
}

Write-Host "=== Vol Diagnostics — Data Migration ===" -ForegroundColor Cyan
Write-Host "Source: $LocalOut"
Write-Host "Target: ${User}@${IP}:${RemoteDir}"
Write-Host ""

# Count files
$files = Get-ChildItem -Recurse -File $LocalOut
Write-Host "Files to transfer: $($files.Count)"
$totalSize = ($files | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "Total size: $([math]::Round($totalSize, 1)) MB"
Write-Host ""

# Create remote directories
Write-Host "[1/3] Creating remote directories..."
ssh -i $KeyFile "${User}@${IP}" "mkdir -p ~/vol-diagnostics/out/surface_history ~/vol-diagnostics/out/vol_index ~/vol-diagnostics/out/gex"

# SCP the data
Write-Host "[2/3] Transferring parquet files..."
scp -i $KeyFile -r "${LocalOut}\*" "${User}@${IP}:${RemoteDir}/"

# Restart and verify
Write-Host "[3/3] Restarting containers and verifying..."
ssh -i $KeyFile "${User}@${IP}" "cd ~/vol-diagnostics && docker compose restart && sleep 5 && docker compose exec dashboard python -m engine.health_check"

Write-Host ""
Write-Host "=== Migration Complete ===" -ForegroundColor Green
Write-Host "Dashboard: http://${IP}"
Write-Host "Health check: ssh -i `"$KeyFile`" ${User}@${IP} `"cd ~/vol-diagnostics && docker compose exec dashboard python -m engine.health_check`""

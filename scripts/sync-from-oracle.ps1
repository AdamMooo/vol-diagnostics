# Vol Diagnostics — pull current out/ data down from Oracle to the local machine.
#
# Oracle's disk is the one source of truth (GitHub Actions writes to it daily via
# .github/workflows/daily-report.yml). This is a one-way refresh for local dev/
# viewing convenience only — nothing local ever collects data anymore since the
# Windows Task Scheduler job was retired in favor of GitHub Actions.
#
# Usage:
#   .\scripts\sync-from-oracle.ps1
#   .\scripts\sync-from-oracle.ps1 -IP "1.2.3.4" -KeyFile "C:\path\to\key"

param(
    [string]$IP      = "40.233.113.63",
    [string]$KeyFile = "$env:USERPROFILE\.ssh\vol-diagnostics.key",
    [string]$User    = "ubuntu"
)

$ErrorActionPreference = "Stop"
$LocalOut = Join-Path $PSScriptRoot "..\out"

if (-not (Test-Path $KeyFile)) {
    Write-Error "SSH key file not found: $KeyFile"
    exit 1
}

Write-Host "=== Vol Diagnostics — Sync FROM Oracle ===" -ForegroundColor Cyan
Write-Host "Source: ${User}@${IP}:~/vol-diagnostics/out/"
Write-Host "Target: $LocalOut"
Write-Host ""

# The dashboard container writes out/ as root (bind mount), so the ubuntu user
# can't read those files directly over scp — stage a chown'd copy first.
Write-Host "[1/3] Staging a readable copy on the server..."
ssh -i $KeyFile "${User}@${IP}" "sudo rm -rf /tmp/out_export && sudo cp -r ~/vol-diagnostics/out /tmp/out_export && sudo chown -R ${User}:${User} /tmp/out_export"

Write-Host "[2/3] Copying down..."
scp -i $KeyFile -r "${User}@${IP}:/tmp/out_export/*" "$LocalOut\"

Write-Host "[3/3] Cleaning up server-side temp copy..."
ssh -i $KeyFile "${User}@${IP}" "sudo rm -rf /tmp/out_export"

Write-Host ""
Write-Host "=== Sync Complete ===" -ForegroundColor Green

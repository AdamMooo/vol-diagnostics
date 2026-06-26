<#
oracle-retry.ps1 — hammer Oracle's "launch instance" API until the Always-Free
ARM shape (VM.Standard.A1.Flex) has capacity, then stop.

Oracle's free A1 tier is chronically "out of host capacity". The console
fails the same way. The reliable fix is to retry the launch API on a loop,
rotating through availability domains, until one accepts. This script does that.

PREREQS (one-time):
  1. Install OCI CLI:
       Invoke-Expression ((Invoke-WebRequest https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.ps1 -UseBasicParsing).Content)
  2. Configure it (creates ~/.oci/config + API key):
       oci setup config
     Follow prompts; upload the generated public key in the OCI console under
     your user → API Keys.
  3. Fill in the CONFIG block below with OCIDs from the OCI console.

WHERE TO FIND EACH OCID:
  CompartmentId : Identity → Compartments (use root/tenancy if unsure)
  SubnetId      : Networking → VCN → your public subnet → OCID
  ImageId       : Compute → Instances → Create → pick Ubuntu 24.04 aarch64,
                  then "Edit YAML" / the image OCID shows in the image picker.
                  Or: oci compute image list --compartment-id <c> --operating-system "Canonical Ubuntu" --shape VM.Standard.A1.Flex
  AvailabilityDomains : run  oci iam availability-domain list  and paste the
                  "name" values (e.g. "abCD:CA-TORONTO-1-AD-1"). List all you have.
  SshKeyPath    : path to your PUBLIC key (.pub). Generate with: ssh-keygen -t ed25519
#>

# ─────────────────────────── CONFIG — EDIT THESE ───────────────────────────
$CompartmentId = "ocid1.tenancy.oc1..aaaaaaaadhfvtdnvcdkaznlke3bsv3ze6gb72cbazmrx7b6747hql3rabcea"
$SubnetId      = "ocid1.subnet.oc1.ca-toronto-1.aaaaaaaalhg2zae2wqx4rbdmxhrj5wioxmxzf75eht2rhrtqndh2lh3v7p3q"  # public subnet-gamma-vcn
$ImageId       = "ocid1.image.oc1.ca-toronto-1.aaaaaaaat2vwds3tqxv6jmx7bhvd4teowruvmhxxigg3pupgxghxz2dgeana"   # Ubuntu 24.04 aarch64
$SshKeyPath    = "$env:USERPROFILE\.ssh\gamma-omm.pub"

$AvailabilityDomains = @(
    "MSYa:CA-TORONTO-1-AD-1"   # ca-toronto-1 has only one AD
)

$DisplayName  = "gamma-omm"
$Shape        = "VM.Standard.A1.Flex"
$Ocpus        = 2
$MemoryGB     = 12
$BootVolGB    = 50        # Oracle minimum is 50GB; still free (Always-Free quota = 200GB total)
$SleepSeconds = 300       # Oracle's launch endpoint rate-limits hard (429) below ~5min
# ────────────────────────────────────────────────────────────────────────────

if (-not (Get-Command oci -ErrorAction SilentlyContinue)) {
    Write-Error "OCI CLI not found. Install it first (see header of this script)."
    exit 1
}
if (-not (Test-Path $SshKeyPath)) {
    Write-Error "SSH public key not found at $SshKeyPath. Generate with: ssh-keygen -t ed25519"
    exit 1
}

$sshKey = (Get-Content $SshKeyPath -Raw).Trim()
$shapeConfig = (@{ ocpus = $Ocpus; memoryInGBs = $MemoryGB } | ConvertTo-Json -Compress)
$attempt = 0
$adIndex = 0

Write-Host "Starting launch-retry loop for $Shape ($Ocpus OCPU / $MemoryGB GB)." -ForegroundColor Cyan
Write-Host "Rotating across $($AvailabilityDomains.Count) AD(s). Ctrl+C to stop.`n"

while ($true) {
    $attempt++
    $ad = $AvailabilityDomains[$adIndex % $AvailabilityDomains.Count]
    $adIndex++
    $ts = (Get-Date).ToString("HH:mm:ss")
    Write-Host "[$ts] attempt #$attempt — AD: $ad ... " -NoNewline

    $out = oci compute instance launch `
        --auth security_token `
        --availability-domain $ad `
        --compartment-id $CompartmentId `
        --shape $Shape `
        --shape-config $shapeConfig `
        --subnet-id $SubnetId `
        --image-id $ImageId `
        --display-name $DisplayName `
        --assign-public-ip true `
        --boot-volume-size-in-gbs $BootVolGB `
        --metadata "{`"ssh_authorized_keys`": `"$sshKey`"}" `
        --wait-for-state RUNNING `
        2>&1 | Out-String

    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS" -ForegroundColor Green
        Write-Host "`nInstance launched. Details:`n"
        Write-Host $out
        Write-Host "`nGet the public IP from the OCI console (Compute → Instances → $DisplayName)." -ForegroundColor Green
        break
    }

    # Only genuine config/account problems are fatal — stop on those so we don't
    # loop forever on a fixable mistake. Everything else (capacity, rate-limit,
    # network timeouts, transient 5xx) is "wait and retry".
    $fatal = "InvalidParameter|NotAuthenticated|NotAuthorized|NotAuthorizedOrNotFound|" +
             "LimitExceeded|QuotaExceeded|CannotParseRequest|MissingParameter"
    if ($out -match $fatal) {
        Write-Host "FATAL (stopping)" -ForegroundColor Red
        Write-Host $out
        Write-Host "`nThis is a config/account problem, not capacity — fix it before retrying." -ForegroundColor Red
        break
    } elseif ($out -match "Out of host capacity") {
        Write-Host "no capacity" -ForegroundColor Yellow
    } elseif ($out -match "TooManyRequests|429") {
        Write-Host "rate-limited (backing off)" -ForegroundColor Yellow
    } else {
        $msg = if ($out -match '"message":\s*"([^"]+)"') { $matches[1] } else { "unknown" }
        Write-Host "transient ($msg) — retrying" -ForegroundColor DarkYellow
    }

    Start-Sleep -Seconds $SleepSeconds
}

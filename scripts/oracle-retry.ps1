<#
oracle-retry.ps1 — hammer Oracle's "launch instance" API until the Always-Free
ARM shape (VM.Standard.A1.Flex) has capacity, then stop.

Oracle's free A1 tier is chronically "out of host capacity". The console
fails the same way. The reliable fix is to retry the launch API on a loop,
rotating through regions AND availability domains, until one accepts.

PREREQS (one-time):
  1. Install OCI CLI:
       Invoke-Expression ((Invoke-WebRequest https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.ps1 -UseBasicParsing).Content)
  2. Configure it (creates ~/.oci/config + API key) under a named profile:
       oci setup config
     Follow prompts, name the profile "vol-diagnostics", use a blank/N-A
     passphrase, and upload the generated public key in the OCI console
     under your user → API Keys.
  3. For each region you want to try beyond Toronto: subscribe the tenancy
     to that region first (Console → top-right region picker → Manage
     Regions), then create a public VCN/subnet there (or let Oracle's
     default one exist) and fill in its entry in $Regions below.

WHERE TO FIND EACH VALUE (per region):
  CompartmentId : Identity → Compartments (same across regions — it's the tenancy root)
  SubnetId      : Networking → VCN → your public subnet → OCID (region-specific)
  ImageId       : oci compute image list --region <region> --compartment-id <c> \
                  --operating-system "Canonical Ubuntu" --shape VM.Standard.A1.Flex \
                  --query "data[0].id" --raw-output
  AvailabilityDomains : oci iam availability-domain list --region <region>
  SshKeyPath    : path to your PUBLIC key (.pub), same key works in every region
#>

# ─────────────────────────── CONFIG — EDIT THESE ───────────────────────────
$CompartmentId = "ocid1.tenancy.oc1..aaaaaaaadhfvtdnvcdkaznlke3bsv3ze6gb72cbazmrx7b6747hql3rabcea"
$SshKeyPath    = "$env:USERPROFILE\.ssh\vol-diagnostics.pub"

# One entry per region to try, in order. Toronto is filled in from the original
# setup. Add Montreal/Ashburn entries once you've subscribed the tenancy to
# that region and created a public subnet there — leave SubnetId/ImageId blank
# ("") to have the script skip a region instead of erroring.
$Regions = @(
    @{
        Region              = "ca-toronto-1"
        SubnetId            = "ocid1.subnet.oc1.ca-toronto-1.aaaaaaaalhg2zae2wqx4rbdmxhrj5wioxmxzf75eht2rhrtqndh2lh3v7p3q"
        ImageId             = "ocid1.image.oc1.ca-toronto-1.aaaaaaaat2vwds3tqxv6jmx7bhvd4teowruvmhxxigg3pupgxghxz2dgeana"
        AvailabilityDomains = @("MSYa:CA-TORONTO-1-AD-1")
    },
    @{
        Region              = "ca-montreal-1"
        SubnetId            = ""   # fill in after subscribing + creating a public subnet
        ImageId             = ""   # oci compute image list --region ca-montreal-1 ...
        AvailabilityDomains = @()  # oci iam availability-domain list --region ca-montreal-1
    },
    @{
        Region              = "us-ashburn-1"
        SubnetId            = ""   # fill in after subscribing + creating a public subnet
        ImageId             = ""   # oci compute image list --region us-ashburn-1 ...
        AvailabilityDomains = @()  # oci iam availability-domain list --region us-ashburn-1 (usually 3 ADs)
    }
)

$DisplayName  = "vol-diagnostics"
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

# Build a flat (region, ad) queue, skipping any region that isn't configured yet.
$targets = @()
foreach ($r in $Regions) {
    if ([string]::IsNullOrWhiteSpace($r.SubnetId) -or [string]::IsNullOrWhiteSpace($r.ImageId) -or $r.AvailabilityDomains.Count -eq 0) {
        Write-Host "Skipping $($r.Region) — SubnetId/ImageId/AvailabilityDomains not filled in yet." -ForegroundColor DarkGray
        continue
    }
    foreach ($ad in $r.AvailabilityDomains) {
        $targets += [pscustomobject]@{ Region = $r.Region; AD = $ad; SubnetId = $r.SubnetId; ImageId = $r.ImageId }
    }
}
if ($targets.Count -eq 0) {
    Write-Error "No fully-configured regions in `$Regions. Fill in at least one beyond Toronto, or check Toronto's config."
    exit 1
}

$sshKey = (Get-Content $SshKeyPath -Raw).Trim()
$shapeConfig = (@{ ocpus = $Ocpus; memoryInGBs = $MemoryGB } | ConvertTo-Json -Compress)
$attempt = 0
$targetIndex = 0

Write-Host "Starting launch-retry loop for $Shape ($Ocpus OCPU / $MemoryGB GB)." -ForegroundColor Cyan
Write-Host "Rotating across $($targets.Count) region/AD combination(s): $(($targets | ForEach-Object { "$($_.Region)/$($_.AD)" }) -join ', ')" -ForegroundColor Cyan
Write-Host "Ctrl+C to stop.`n"

while ($true) {
    $attempt++
    $t = $targets[$targetIndex % $targets.Count]
    $targetIndex++
    $ts = (Get-Date).ToString("HH:mm:ss")
    Write-Host "[$ts] attempt #$attempt — region: $($t.Region), AD: $($t.AD) ... " -NoNewline

    $out = oci compute instance launch `
        --profile vol-diagnostics `
        --region $t.Region `
        --availability-domain $t.AD `
        --compartment-id $CompartmentId `
        --shape $Shape `
        --shape-config $shapeConfig `
        --subnet-id $t.SubnetId `
        --image-id $t.ImageId `
        --display-name $DisplayName `
        --assign-public-ip true `
        --boot-volume-size-in-gbs $BootVolGB `
        --metadata "{`"ssh_authorized_keys`": `"$sshKey`"}" `
        --wait-for-state RUNNING `
        2>&1 | Out-String

    if ($LASTEXITCODE -eq 0) {
        Write-Host "SUCCESS" -ForegroundColor Green
        Write-Host "`nInstance launched in $($t.Region). Details:`n"
        Write-Host $out
        Write-Host "`nGet the public IP from the OCI console (Compute → Instances → $DisplayName, region switcher top-right)." -ForegroundColor Green
        Write-Host "Next: run scripts/migrate-to-new-instance.ps1 -NewIP <ip> -Region $($t.Region) to move the stack over." -ForegroundColor Green
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
        Write-Host "no capacity ($($t.Region))" -ForegroundColor Yellow
    } elseif ($out -match "TooManyRequests|429") {
        Write-Host "rate-limited (backing off)" -ForegroundColor Yellow
    } else {
        $msg = if ($out -match '"message":\s*"([^"]+)"') { $matches[1] } else { "unknown" }
        Write-Host "transient ($msg) — retrying" -ForegroundColor DarkYellow
    }

    Start-Sleep -Seconds $SleepSeconds
}

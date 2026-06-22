# Register the GEX daily email as a Windows Task Scheduler task.
# Run once from a normal (non-admin) PowerShell terminal:
#   C:\dev\gamma-omm\runners\gex_daily.ps1 activate
#   C:\dev\gamma-omm\runners\gex_daily.ps1 deactivate
#   C:\dev\gamma-omm\runners\gex_daily.ps1 status
param([Parameter(Position=0)][string]$cmd = "activate")

$TaskName   = "GEX Daily Report"
$ProjectDir = "C:\dev\gamma-omm"
$Python     = "$ProjectDir\.venv\Scripts\python.exe"
$Script     = "-m engine.run_daily --send"

if ($cmd -eq "activate") {
    $action   = New-ScheduledTaskAction -Execute $Python -Argument $Script -WorkingDirectory $ProjectDir
    $trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "16:30"
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Force
    Write-Host "Activated: $TaskName - runs daily at 4:30 PM"
    exit 0
}

if ($cmd -eq "deactivate") {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Deactivated: $TaskName"
    exit 0
}

if ($cmd -eq "status") {
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Host "State      : $($task.State)"
        Write-Host "Last run   : $($info.LastRunTime)"
        Write-Host "Last result: $($info.LastTaskResult)"
        Write-Host "Next run   : $($info.NextRunTime)"
    } else {
        Write-Host "$TaskName is not registered."
    }
    exit 0
}

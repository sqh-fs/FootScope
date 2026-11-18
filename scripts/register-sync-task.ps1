$ErrorActionPreference = 'Stop'

$taskName = 'FootScope Data Sync'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw 'Create the project virtual environment before registering the task.'
}

$existing = Get-ScheduledTask -TaskName $taskName -TaskPath '\' -ErrorAction SilentlyContinue
if ($existing -and ($existing.Actions.Count -ne 1 -or
        $existing.Actions[0].Execute -ne $python -or
        $existing.Actions[0].WorkingDirectory -ne $projectRoot)) {
    throw 'A scheduled task with this name already belongs to a different installation.'
}

$taskUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $taskUser -LogonType Interactive -RunLevel Limited
$action = New-ScheduledTaskAction -Execute $python -WorkingDirectory $projectRoot `
    -Argument '-X utf8 -m backend sync --log-file data\sync.log'
$firstRun = (Get-Date).AddHours(2)
$trigger = New-ScheduledTaskTrigger -Once -At $firstRun `
    -RepetitionInterval (New-TimeSpan -Hours 2)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $taskName -TaskPath '\' -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Description 'Refresh the FootScope Premier League data every two hours.' `
    -Force | Out-Null

Get-ScheduledTaskInfo -TaskName $taskName -TaskPath '\' | Select-Object TaskName, NextRunTime

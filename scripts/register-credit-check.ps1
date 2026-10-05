# Registers a per-user scheduled task that runs codex-credit-check.py every 30 minutes,
# so a Codex account that runs out of credits drops out of the proxy's rotation on its own
# and comes back when credits are refilled. Run once from PowerShell:
#   powershell -ExecutionPolicy Bypass -File <repo>\scripts\register-credit-check.ps1
# Remove with:  Unregister-ScheduledTask -TaskName CodexCreditCheck -Confirm:$false
$python = (Get-Command python).Source
$script = Join-Path $PSScriptRoot "codex-credit-check.py"
$action = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory (Split-Path $script)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30)
$settings = New-ScheduledTaskSettingsSet -Hidden -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -StartWhenAvailable
Register-ScheduledTask -TaskName "CodexCreditCheck" -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
Get-ScheduledTask -TaskName "CodexCreditCheck" | Select-Object TaskName, State

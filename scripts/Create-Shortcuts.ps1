$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$PowerShell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$Shell = New-Object -ComObject WScript.Shell

function New-AstroPulseShortcut([string]$Path, [string]$ScriptName) {
    $ScriptPath = Join-Path $Root $ScriptName
    $Shortcut = $Shell.CreateShortcut($Path)
    $Shortcut.TargetPath = $PowerShell
    $Shortcut.Arguments = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
    $Shortcut.WorkingDirectory = $Root
    $Shortcut.IconLocation = "$PowerShell,0"
    $Shortcut.Description = 'AstroPulse local mission control launcher'
    $Shortcut.Save()
}

New-AstroPulseShortcut (Join-Path $Root 'Start AstroPulse.lnk') 'Start AstroPulse.ps1'
New-AstroPulseShortcut (Join-Path $Root 'Stop AstroPulse.lnk') 'Stop AstroPulse.ps1'
Write-Host 'Created start and stop shortcuts in the AstroPulse project folder.' -ForegroundColor Green

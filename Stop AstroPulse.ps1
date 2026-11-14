$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime = Join-Path $Root 'runtime'
$StatePath = Join-Path $Runtime 'processes.json'

if (-not (Test-Path -LiteralPath $StatePath)) {
    Write-Host 'AstroPulse is not running from this launcher.' -ForegroundColor Yellow
    Read-Host 'Press Enter to close this window'
    exit 0
}

$Stopped = 0
try {
    $State = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
    if ($State -is [array]) {
        $Entries = $State
    } elseif ($State.processes) {
        $Entries = $State.processes
    } elseif ($State.name) {
        $Entries = @($State)
    } else {
        $Entries = @()
    }
    foreach ($Entry in $Entries) {
        try {
            $Process = Get-CimInstance Win32_Process -Filter "ProcessId = $($Entry.pid)" -ErrorAction Stop
            if ($Process -and $Process.CommandLine -and $Process.CommandLine.Contains([string]$Entry.script)) {
                & taskkill.exe /PID ([int]$Entry.pid) /T /F | Out-Null
                $Stopped++
            }
        } catch {
            # The service may already have stopped.
        }
    }
} finally {
    Remove-Item -LiteralPath $StatePath -Force -ErrorAction SilentlyContinue
}

Write-Host "Stopped $Stopped AstroPulse service process(es)." -ForegroundColor Green
Read-Host 'Press Enter to close this window'

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Runtime = Join-Path $Root 'runtime'
$Logs = Join-Path $Runtime 'logs'
$StatePath = Join-Path $Runtime 'processes.json'
$PortsPath = Join-Path $Runtime 'ports.json'
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$Frontend = Join-Path $Root '5_frontend_hud'
$Backend = Join-Path $Root '3_backend_core'
$Scripts = Join-Path $Root 'scripts'
$PowerShell = (Get-Process -Id $PID).Path
$Started = [System.Collections.Generic.List[object]]::new()
$Existing = [System.Collections.Generic.List[object]]::new()
$BackendPort = 0
$FrontendPort = 0
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:NUMEXPR_NUM_THREADS = '1'
$env:BLAS_NUM_THREADS = '1'

function Write-Stage([string]$Message) {
    Write-Host "`n>> $Message" -ForegroundColor Cyan
}

function Test-ProcessFromProject([object]$Entry) {
    if (-not $Entry.pid -or -not $Entry.script) { return $false }
    try {
        $Process = Get-CimInstance Win32_Process -Filter "ProcessId = $($Entry.pid)" -ErrorAction Stop
        return ($Process -and $Process.CommandLine -and $Process.CommandLine.Contains([string]$Entry.script))
    } catch {
        return $false
    }
}

function Stop-ProjectProcess([object]$Entry) {
    if (Test-ProcessFromProject $Entry) {
        & taskkill.exe /PID ([int]$Entry.pid) /T /F | Out-Null
        Write-Host "Stopped an older AstroPulse $($Entry.name) process." -ForegroundColor DarkYellow
    }
}

function Save-ProcessState {
    $AllProcesses = @($Existing.ToArray()) + @($Started.ToArray())
    $State = [pscustomobject]@{
        backendPort = [int]$BackendPort
        frontendPort = [int]$FrontendPort
        processes = [object[]]$AllProcesses
    }
    $State | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8
}

function Find-FreePort([int]$FirstPort, [int]$LastPort) {
    for ($Port = $FirstPort; $Port -le $LastPort; $Port++) {
        $Listener = $null
        try {
            $Listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
            $Listener.Start()
            return $Port
        } catch {
            # Try the next port when another application already owns this one.
        } finally {
            if ($Listener) { $Listener.Stop() }
        }
    }
    throw "No free local port found between $FirstPort and $LastPort."
}

function Start-HiddenService([string]$Name, [string]$ScriptName) {
    $ScriptPath = Join-Path $Scripts $ScriptName
    $Stdout = Join-Path $Logs "$Name.out.log"
    $Stderr = Join-Path $Logs "$Name.err.log"
    $Process = Start-Process -FilePath $PowerShell `
        -ArgumentList @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $ScriptPath) `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $Stdout `
        -RedirectStandardError $Stderr `
        -WindowStyle Hidden `
        -PassThru
    $Started.Add([pscustomobject]@{ name = $Name; pid = $Process.Id; script = $ScriptPath })
    Save-ProcessState
    Write-Host "Started $Name (process $($Process.Id))." -ForegroundColor Green
}

function Test-BackendReady([int]$Port) {
    try {
        $Reply = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/" -TimeoutSec 2
        return $Reply.service -eq 'AstroPulse Core Backend'
    } catch { return $false }
}

function Test-FrontendReady([int]$Port) {
    try {
        $Reply = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -TimeoutSec 2 -UseBasicParsing
        return ($Reply.StatusCode -eq 200 -and
            $Reply.Content.Contains('AstroPulse') -and
            $Reply.Content.Contains('/src/main.jsx'))
    } catch { return $false }
}

function Wait-For([scriptblock]$Check, [string]$Name) {
    for ($Attempt = 0; $Attempt -lt 45; $Attempt++) {
        if (& $Check) { return $true }
        Start-Sleep -Seconds 1
    }
    throw "$Name did not become ready. Check the log files in '$Logs'."
}

try {
    Write-Host 'AstroPulse one-click startup' -ForegroundColor White
    Write-Host "Project folder: $Root" -ForegroundColor DarkGray
    New-Item -ItemType Directory -Force -Path $Logs | Out-Null

    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw 'Python Launcher (py) is missing. Install Python for Windows, then run this icon again.'
    }
    if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw 'Node.js and npm are required for the AstroPulse dashboard. Install Node.js, then run this icon again.'
    }

    Write-Stage 'Preparing the Python environment'
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        & py -m venv (Join-Path $Root '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment.' }
    }
    & $VenvPython -m pip install -r (Join-Path $Backend 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the backend packages. Check your internet connection and try again.' }

    Write-Stage 'Preparing the dashboard'
    if (-not (Test-Path -LiteralPath (Join-Path $Frontend 'node_modules'))) {
        Push-Location -LiteralPath $Frontend
        try {
            & npm.cmd ci
            if ($LASTEXITCODE -ne 0) { throw 'Could not install the dashboard packages.' }
        } finally {
            Pop-Location
        }
    }

    if (-not (Test-Path -LiteralPath (Join-Path $Backend 'astropulse_ai_engine.pkl'))) {
        Write-Stage 'Training the local telemetry model from the bundled dataset'
        & $VenvPython (Join-Path $Backend 'train_model.py')
        if ($LASTEXITCODE -ne 0) { throw 'The telemetry model could not be created. Check the dataset and try again.' }
    }

    $OldState = $null
    if (Test-Path -LiteralPath $StatePath) {
        try {
            $OldState = Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json
            if ($OldState -is [array]) {
                foreach ($Entry in $OldState) {
                    if (Test-ProcessFromProject $Entry) { $Existing.Add($Entry) }
                }
            } elseif ($OldState.processes) {
                foreach ($Entry in $OldState.processes) {
                    if (Test-ProcessFromProject $Entry) { $Existing.Add($Entry) }
                }
            } elseif ($OldState.name -and (Test-ProcessFromProject $OldState)) {
                # Older launcher versions wrote a single process record without port metadata.
                $Existing.Add($OldState)
            }
        } catch {
            Write-Host 'Old launch state could not be read; starting with new ports.' -ForegroundColor Yellow
        }
    }

    $ReuseExisting = $false
    if ($OldState -and $OldState.backendPort -and $OldState.frontendPort) {
        $HasBackend = @($Existing | Where-Object { $_.name -eq 'backend' }).Count -gt 0
        $HasFrontend = @($Existing | Where-Object { $_.name -eq 'frontend' }).Count -gt 0
        $BackendPort = [int]$OldState.backendPort
        $FrontendPort = [int]$OldState.frontendPort
        $ReuseExisting = ($HasBackend -and $HasFrontend -and
            (Test-BackendReady $BackendPort) -and (Test-FrontendReady $FrontendPort))
    }

    if (-not $ReuseExisting) {
        foreach ($Entry in $Existing) { Stop-ProjectProcess $Entry }
        $Existing.Clear()
        Write-Stage 'Choosing AstroPulse-only local ports'
        $BackendPort = Find-FreePort 8180 8280
        $FrontendPort = Find-FreePort 5180 5280
    }

    [pscustomobject]@{ backendPort = $BackendPort; frontendPort = $FrontendPort } |
        ConvertTo-Json | Set-Content -LiteralPath $PortsPath -Encoding UTF8
    Save-ProcessState

    Write-Stage 'Starting the API and dashboard'
    if (-not (Test-BackendReady $BackendPort)) { Start-HiddenService 'backend' 'run-backend.ps1' }
    Wait-For { Test-BackendReady $BackendPort } 'AstroPulse backend'

    if (-not (Test-FrontendReady $FrontendPort)) { Start-HiddenService 'frontend' 'run-frontend.ps1' }
    Wait-For { Test-FrontendReady $FrontendPort } 'AstroPulse dashboard'

    $SimulatorRunning = @($Existing | Where-Object { $_.name -eq 'simulator' }).Count -gt 0
    if (-not $SimulatorRunning) {
        Start-HiddenService 'simulator' 'run-simulator.ps1'
        Start-Sleep -Seconds 4
        $SimulatorEntry = $Started | Where-Object { $_.name -eq 'simulator' } | Select-Object -First 1
        if (-not (Get-Process -Id $SimulatorEntry.pid -ErrorAction SilentlyContinue)) {
            throw "Telemetry simulator stopped during startup. Check '$Logs\simulator.err.log'."
        }
    }

    Save-ProcessState
    Write-Stage 'AstroPulse is running'
    $DashboardUrl = "http://127.0.0.1:$FrontendPort/"
    Write-Host "Dashboard: $DashboardUrl" -ForegroundColor Green
    Write-Host "API docs:  http://127.0.0.1:$BackendPort/docs" -ForegroundColor Green
    Start-Process $DashboardUrl
    Write-Host "`nAstroPulse is using its own ports. The other local project can keep running." -ForegroundColor DarkGray
} catch {
    Write-Host "`nAstroPulse could not start: $($_.Exception.Message)" -ForegroundColor Red
    foreach ($Log in Get-ChildItem -LiteralPath $Logs -Filter '*.err.log' -ErrorAction SilentlyContinue) {
        $Recent = Get-Content -LiteralPath $Log.FullName -Tail 8 -ErrorAction SilentlyContinue
        if ($Recent) { Write-Host "`n$($Log.Name):`n$($Recent -join "`n")" -ForegroundColor DarkYellow }
    }
    Read-Host 'Press Enter to close this window'
    exit 1
}

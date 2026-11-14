$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Simulator = Join-Path $Root '2_telemetry_simulator\simulator.py'
$Ports = Get-Content -LiteralPath (Join-Path $Root 'runtime\ports.json') -Raw | ConvertFrom-Json
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:NUMEXPR_NUM_THREADS = '1'
$env:BLAS_NUM_THREADS = '1'
$env:PYTHONIOENCODING = 'utf-8'
Set-Location -LiteralPath $Root
& $Python $Simulator --crisis-demo --url "http://127.0.0.1:$($Ports.backendPort)/api/telemetry"

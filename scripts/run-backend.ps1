$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$Backend = Join-Path $Root '3_backend_core'
$Ports = Get-Content -LiteralPath (Join-Path $Root 'runtime\ports.json') -Raw | ConvertFrom-Json
$env:PYTHONUNBUFFERED = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:NUMEXPR_NUM_THREADS = '1'
$env:BLAS_NUM_THREADS = '1'
Set-Location -LiteralPath $Backend
& $Python -m uvicorn main:app --host 127.0.0.1 --port ([int]$Ports.backendPort)

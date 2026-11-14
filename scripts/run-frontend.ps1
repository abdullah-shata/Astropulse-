$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root '5_frontend_hud'
$Ports = Get-Content -LiteralPath (Join-Path $Root 'runtime\ports.json') -Raw | ConvertFrom-Json
$env:ASTROPULSE_BACKEND_PORT = [string]$Ports.backendPort
$env:ASTROPULSE_FRONTEND_PORT = [string]$Ports.frontendPort
Set-Location -LiteralPath $Frontend
& npm.cmd run dev -- --host 127.0.0.1 --port ([int]$Ports.frontendPort) --strictPort

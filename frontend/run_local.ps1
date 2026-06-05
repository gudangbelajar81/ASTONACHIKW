# PowerShell script to install dependencies and run frontend (Windows)
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Installing frontend dependencies..."
npm install --no-audit --no-fund --strict-ssl=false --cache .\.npm-cache

Write-Host "Starting frontend (next)..."
npm run dev

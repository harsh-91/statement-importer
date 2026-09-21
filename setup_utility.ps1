# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $projectRoot '.venv'
$python = Join-Path $venv 'Scripts\python.exe'

if (-not (Test-Path -LiteralPath $python)) {
    py -3 -m venv $venv
}

& $python -m pip install --upgrade pip
& $python -m pip install -r (Join-Path $projectRoot 'requirements.txt')
& $python (Join-Path $projectRoot 'app.py') --migrate-only
Write-Host 'Setup complete. Run .\run_utility.ps1 to open the importer.'

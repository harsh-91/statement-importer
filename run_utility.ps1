# Created by Harsh (@harsh-91) | Made in India
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Utility dependencies are not installed. Run .\setup_utility.ps1 first.'
}
& $python (Join-Path $projectRoot 'app.py') --open-browser

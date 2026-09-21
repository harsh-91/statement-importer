# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    py -3 -m venv (Join-Path $projectRoot '.venv')
}
& $python -m pip install -r (Join-Path $projectRoot 'requirements-build-lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name StatementImporter `
    --add-data "templates;templates" --add-data "static;static" --collect-all webview desktop.py
if ($LASTEXITCODE -ne 0) { throw 'StatementImporter.exe build failed. Close any running copy and retry.' }
New-Item -ItemType Directory -Path (Join-Path $projectRoot 'setup-payload') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'dist\StatementImporter.exe') -Destination (Join-Path $projectRoot 'setup-payload\StatementImporter.exe') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'QUICK_START.txt') -Destination (Join-Path $projectRoot 'setup-payload\QUICK_START.txt') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE.md') -Destination (Join-Path $projectRoot 'setup-payload\LICENSE.md') -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'NOTICE') -Destination (Join-Path $projectRoot 'setup-payload\NOTICE') -Force
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name StatementImporterSetup `
    --add-data "setup-payload;payload" setup_launcher.py
if ($LASTEXITCODE -ne 0) { throw 'StatementImporterSetup.exe build failed. Close any running copy and retry.' }
Write-Host "Built: $projectRoot\dist\StatementImporter.exe"
Write-Host "Built: $projectRoot\dist\StatementImporterSetup.exe"
Copy-Item -LiteralPath (Join-Path $projectRoot 'requirements-lock.txt') -Destination (Join-Path $projectRoot 'dist\DEPENDENCY_MANIFEST.txt') -Force
$localIscc = Join-Path $projectRoot 'tools\inno\ISCC.exe'
$installedIscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
$installedIscc7 = Join-Path $env:ProgramFiles 'Inno Setup 7\ISCC.exe'
$registeredIscc = Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall','HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall' -ErrorAction SilentlyContinue |
    Get-ItemProperty -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -like 'Inno Setup 7*' -and $_.InstallLocation } |
    ForEach-Object { Join-Path $_.InstallLocation 'ISCC.exe' } |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
$iscc = @($localIscc, $registeredIscc, $installedIscc7, $installedIscc) | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if ($iscc) {
    & $iscc (Join-Path $projectRoot 'installer\StatementImporter.iss')
    if ($LASTEXITCODE -ne 0) { throw 'Conventional installer build failed.' }
    Write-Host "Built: $projectRoot\dist\StatementImporter-1.3.5-Setup-x64.exe"
} else {
    Write-Warning 'Inno Setup compiler not found; conventional installer was not built.'
}

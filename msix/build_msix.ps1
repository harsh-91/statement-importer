# Created by Harsh (@harsh-91) | Made in India | SPDX-License-Identifier: Apache-2.0
[CmdletBinding()]
param(
    [string]$IdentityName = $(if ($env:MSIX_IDENTITY_NAME) { $env:MSIX_IDENTITY_NAME } else { 'HarshNair.NeonLedger' }),
    [string]$Publisher = $(if ($env:MSIX_PUBLISHER) { $env:MSIX_PUBLISHER } else { 'CN=Harsh Nair' }),
    [string]$PostgresArchive,
    [switch]$SkipAppBuild
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$stagingRoot = Join-Path $projectRoot 'build\msix-layout'
$appBuildRoot = Join-Path $projectRoot 'build\msix-app'
$distRoot = Join-Path $projectRoot 'dist'
$cacheRoot = Join-Path $projectRoot '.cache'
$postgresUrl = 'https://get.enterprisedb.com/postgresql/postgresql-17.11-4-windows-x64-binaries.zip'
$postgresSha256 = 'B9424EE7BC60B52450FF910A3630225DF32E633F3CB29C1D126D9299D59AEA28'

if (-not $PostgresArchive) {
    $PostgresArchive = Join-Path $cacheRoot 'postgresql-17.11-4-windows-x64-binaries.zip'
}

$versionSource = Get-Content -Raw (Join-Path $projectRoot 'statement_importer\version.py')
$match = [regex]::Match($versionSource, '__version__\s*=\s*"(?<version>\d+\.\d+\.\d+)"')
if (-not $match.Success) { throw 'Could not read the application version.' }
$appVersion = $match.Groups['version'].Value
$packageVersion = "$appVersion.0"
$outputPackage = Join-Path $distRoot "NeonLedger-$appVersion-x64.msix"

if (-not $SkipAppBuild) {
    $python = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'Build environment missing. Create .venv and install requirements-build-lock.txt.' }
    if (Test-Path -LiteralPath $appBuildRoot) { Remove-Item -LiteralPath $appBuildRoot -Recurse -Force }
    & $python -m PyInstaller --noconfirm --clean --onedir --contents-directory . `
        --distpath $appBuildRoot --workpath (Join-Path $projectRoot 'build\msix-pyinstaller') `
        --name StatementImporter --add-data 'templates;templates' --add-data 'static;static' `
        --collect-all webview (Join-Path $projectRoot 'desktop.py')
    if ($LASTEXITCODE -ne 0) { throw 'The MSIX application build failed.' }
}

$appSource = Join-Path $appBuildRoot 'StatementImporter'
if (-not (Test-Path -LiteralPath (Join-Path $appSource 'StatementImporter.exe'))) {
    throw 'The MSIX application payload is missing.'
}

New-Item -ItemType Directory -Path $cacheRoot,$distRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $PostgresArchive)) {
    Write-Host 'Downloading the pinned PostgreSQL redistributable archive...'
    Invoke-WebRequest -Uri $postgresUrl -OutFile $PostgresArchive
}
$actualPostgresHash = (Get-FileHash -LiteralPath $PostgresArchive -Algorithm SHA256).Hash
if ($actualPostgresHash -ne $postgresSha256) {
    throw "PostgreSQL archive verification failed. Expected $postgresSha256 but received $actualPostgresHash."
}

$resolvedStaging = [IO.Path]::GetFullPath($stagingRoot)
$resolvedBuild = [IO.Path]::GetFullPath((Join-Path $projectRoot 'build'))
if (-not $resolvedStaging.StartsWith($resolvedBuild, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Refusing to clean an MSIX staging path outside the project build directory.'
}
if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
New-Item -ItemType Directory -Path (Join-Path $stagingRoot 'app'),(Join-Path $stagingRoot 'Assets') -Force | Out-Null
Copy-Item -Path (Join-Path $appSource '*') -Destination (Join-Path $stagingRoot 'app') -Recurse -Force

$postgresExtract = Join-Path $projectRoot 'build\postgresql-extract'
if (Test-Path -LiteralPath $postgresExtract) { Remove-Item -LiteralPath $postgresExtract -Recurse -Force }
Expand-Archive -LiteralPath $PostgresArchive -DestinationPath $postgresExtract
$postgresRoot = Get-ChildItem -LiteralPath $postgresExtract -Directory |
    Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'bin\postgres.exe') } |
    Select-Object -First 1
if (-not $postgresRoot) { throw 'The verified PostgreSQL archive did not contain the expected server binaries.' }
Copy-Item -LiteralPath $postgresRoot.FullName -Destination (Join-Path $stagingRoot 'app\postgresql') -Recurse -Force

Add-Type -AssemblyName System.Drawing
function New-NeonAsset([string]$Path, [int]$Width, [int]$Height) {
    $bitmap = [Drawing.Bitmap]::new($Width, $Height)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.Clear([Drawing.Color]::FromArgb(16, 21, 36))
        $scale = [Math]::Max(1, [Math]::Floor([Math]::Min($Width, $Height) / 12))
        $x = [Math]::Floor(($Width - 8 * $scale) / 2)
        $y = [Math]::Floor(($Height - 8 * $scale) / 2)
        $cyan = [Drawing.SolidBrush]::new([Drawing.Color]::FromArgb(44, 246, 220))
        $magenta = [Drawing.SolidBrush]::new([Drawing.Color]::FromArgb(255, 61, 172))
        try {
            $graphics.FillRectangle($magenta, $x, $y, 8 * $scale, 8 * $scale)
            $graphics.FillRectangle($cyan, $x + $scale, $y + $scale, 2 * $scale, 6 * $scale)
            $graphics.FillRectangle($cyan, $x + 5 * $scale, $y + $scale, 2 * $scale, 6 * $scale)
            $graphics.FillRectangle($cyan, $x + 3 * $scale, $y + 3 * $scale, 2 * $scale, 2 * $scale)
            $graphics.FillRectangle($cyan, $x + 4 * $scale, $y + 4 * $scale, 2 * $scale, 2 * $scale)
        } finally {
            $cyan.Dispose(); $magenta.Dispose()
        }
        $bitmap.Save($Path, [Drawing.Imaging.ImageFormat]::Png)
    } finally {
        $graphics.Dispose(); $bitmap.Dispose()
    }
}

$assets = Join-Path $stagingRoot 'Assets'
New-NeonAsset (Join-Path $assets 'StoreLogo.png') 50 50
New-NeonAsset (Join-Path $assets 'Square44x44Logo.png') 44 44
New-NeonAsset (Join-Path $assets 'Square150x150Logo.png') 150 150
New-NeonAsset (Join-Path $assets 'Wide310x150Logo.png') 310 150
New-NeonAsset (Join-Path $assets 'SplashScreen.png') 620 300

$manifest = Get-Content -Raw (Join-Path $projectRoot 'msix\AppxManifest.xml.in')
$manifest = $manifest.Replace('{{IDENTITY_NAME}}', $IdentityName).Replace('{{PUBLISHER}}', $Publisher).Replace('{{VERSION}}', $packageVersion)
[IO.File]::WriteAllText((Join-Path $stagingRoot 'AppxManifest.xml'), $manifest, [Text.UTF8Encoding]::new($false))
Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE.md') -Destination (Join-Path $stagingRoot 'app\LICENSE.md')
Copy-Item -LiteralPath (Join-Path $projectRoot 'NOTICE') -Destination (Join-Path $stagingRoot 'app\NOTICE')

$kitsRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10\bin'
$makeAppx = Get-ChildItem -LiteralPath $kitsRoot -Filter MakeAppx.exe -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match '\\x64\\MakeAppx\.exe$' } |
    Sort-Object FullName -Descending | Select-Object -First 1
if (-not $makeAppx) { throw 'MakeAppx.exe was not found. Install the Windows SDK or build on GitHub Actions.' }
if (Test-Path -LiteralPath $outputPackage) { Remove-Item -LiteralPath $outputPackage -Force }
& $makeAppx.FullName pack /d $stagingRoot /p $outputPackage /o
if ($LASTEXITCODE -ne 0) { throw 'MakeAppx failed to create the package.' }

$hash = (Get-FileHash -LiteralPath $outputPackage -Algorithm SHA256).Hash
Set-Content -LiteralPath "$outputPackage.sha256" -Value "$hash  $(Split-Path -Leaf $outputPackage)" -Encoding ascii
Write-Host "Built unsigned Store submission package: $outputPackage"
Write-Host "SHA-256: $hash"

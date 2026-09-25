# Created by Harsh Nair | Made in India | SPDX-License-Identifier: Apache-2.0
param(
    [Parameter(Mandatory=$true)][string]$Executable,
    [Parameter(Mandatory=$true)][string]$ResultPath,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$targetPath = [IO.Path]::GetFullPath($Executable)
$timer = [Diagnostics.Stopwatch]::StartNew()
function Canonical-Path([string]$Path) {
    try { (Get-Item -LiteralPath $Path -Force).FullName }
    catch { [IO.Path]::GetFullPath($Path) }
}
$targetPath = Canonical-Path $targetPath
function Find-Target {
    $name = [IO.Path]::GetFileNameWithoutExtension($targetPath)
    $matches = [Collections.Generic.Dictionary[int,Diagnostics.Process]]::new()
    foreach ($process in @(Get-Process -Name $name -ErrorAction SilentlyContinue)) {
        $candidate = $null
        try { $candidate = $process.Path } catch { }
        if (-not $candidate) { try { $candidate = $process.MainModule.FileName } catch { } }
        if ($candidate -and [string]::Equals((Canonical-Path $candidate), $targetPath, [StringComparison]::OrdinalIgnoreCase)) {
            $matches[$process.Id] = $process
        }
    }
    if ($matches.Count -eq 0) {
        foreach ($item in @(Get-CimInstance Win32_Process -Filter "Name='$([IO.Path]::GetFileName($targetPath))'" -ErrorAction SilentlyContinue)) {
            if ($item.ExecutablePath -and [string]::Equals((Canonical-Path $item.ExecutablePath), $targetPath, [StringComparison]::OrdinalIgnoreCase)) {
                $process = Get-Process -Id $item.ProcessId -ErrorAction SilentlyContinue
                if ($process) { $matches[$process.Id] = $process }
            }
        }
    }
    @($matches.Values)
}
try {
    foreach ($process in (Find-Target)) {
        if ($Force) {
            try { $process.Kill($true) } catch { $process.Kill() }
            try { [void]$process.WaitForExit(5000) } catch { }
        } else { [void]$process.CloseMainWindow() }
    }
    do {
        if ((Find-Target).Count -eq 0) {
            try {
                $probe = [IO.File]::Open($targetPath, 'Open', 'ReadWrite', 'None')
                $probe.Dispose()
                [IO.File]::WriteAllText($ResultPath, 'ready')
                exit 0
            } catch [IO.IOException] { }
        }
        Start-Sleep -Milliseconds 200
    } while ($timer.Elapsed.TotalSeconds -lt 12)
    [IO.File]::WriteAllText($ResultPath, 'busy')
} catch {
    # No credentials or process command lines are written to the installer log.
    [IO.File]::WriteAllText($ResultPath, 'error')
}

# Created by Harsh Nair | Made in India | SPDX-License-Identifier: Apache-2.0
param(
    [Parameter(Mandatory=$true)][string]$Executable,
    [Parameter(Mandatory=$true)][string]$ResultPath,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$targetPath = [IO.Path]::GetFullPath($Executable)
$timer = [Diagnostics.Stopwatch]::StartNew()
function Find-Target {
    @(Get-Process -Name ([IO.Path]::GetFileNameWithoutExtension($targetPath)) -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and [string]::Equals($_.Path, $targetPath, [StringComparison]::OrdinalIgnoreCase) })
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

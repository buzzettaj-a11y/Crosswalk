# Writes wholecount-offline.wsb from the template (M14 section 8). A .wsb file needs absolute host paths, so it is made per
# machine and never committed. Copies sandbox_run.ps1 into the installer folder so the sandbox can run it.
param([Parameter(Mandatory = $true)][string]$InstallerDir, [Parameter(Mandatory = $true)][string]$ResultsDir)
$ErrorActionPreference = "Stop"
$in = (Resolve-Path $InstallerDir).Path
New-Item -ItemType Directory -Force $ResultsDir | Out-Null
$out = (Resolve-Path $ResultsDir).Path
Copy-Item (Join-Path $PSScriptRoot "sandbox_run.ps1") $in -Force
$text = (Get-Content (Join-Path $PSScriptRoot "wholecount-offline.wsb.in") -Raw).Replace("@INSTALLER_DIR@", $in).Replace("@RESULTS_DIR@", $out)
$wsb = Join-Path $PSScriptRoot "wholecount-offline.wsb"
Set-Content $wsb $text -Encoding utf8
Write-Host "Wrote $wsb. Double-click it to start Windows Sandbox with networking off."

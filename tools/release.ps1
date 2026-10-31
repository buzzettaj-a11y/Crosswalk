# Joe's one command (M14 section 5): build, sign the exe, compile the installer with the signed exe, sign the installer, and
# print both SHA-256 values and signature states. Not run in the cloud session.
param([switch]$NoTimestamp)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (-not $env:VIRTUAL_ENV) { throw "Activate the .venv first: .venv\Scripts\activate" }

& tools\build.ps1 -NoInstaller
$signFlags = @{}
if ($NoTimestamp) { $signFlags["NoTimestamp"] = $true }
& tools\sign.ps1 -Path dist\Wholecount\Wholecount.exe @signFlags
$self = (Resolve-Path tools\sign.ps1).Path
$ts = if ($NoTimestamp) { " -NoTimestamp" } else { "" }
& tools\build.ps1 -SignTool "pwsh -NoProfile -File `"$self`"$ts -Path `$f"
$installer = Get-ChildItem Output\Wholecount-Setup-*.exe | Sort-Object LastWriteTime -Descending | Select-Object -First 1
& tools\sign.ps1 -Path $installer.FullName @signFlags
foreach ($f in @("dist\Wholecount\Wholecount.exe", $installer.FullName)) {
    $hash = (Get-FileHash $f -Algorithm SHA256).Hash
    $sig = (Get-AuthenticodeSignature $f).Status
    Write-Host "$f  SHA256 $hash  signature $sig"
}

# Signs one file (M14 section 5, docs/SIGNING.md). Sources: Microsoft, SignTool and Get-AuthenticodeSignature.
# The only network use is the timestamp request from this machine at build time. Not run in the cloud session.
param([Parameter(Mandatory = $true)][string]$Path, [switch]$NoTimestamp, [string]$Thumbprint = "")
$ErrorActionPreference = "Stop"
$settings = Get-Content (Join-Path $PSScriptRoot "signing.json") -Raw | ConvertFrom-Json -AsHashtable
$local = Join-Path $PSScriptRoot "signing.local.json"
if (Test-Path $local) { (Get-Content $local -Raw | ConvertFrom-Json -AsHashtable).GetEnumerator() | ForEach-Object { $settings[$_.Key] = $_.Value } }
if (-not $Thumbprint) { $Thumbprint = $settings["thumbprint"] }

if ($settings["provider"] -eq "azure_artifact_signing") {
    # Unconfirmed: written from Microsoft's Artifact Signing documentation; nothing here could run it.
    throw "Azure Artifact Signing is not set up on this machine yet. See docs\SIGNING.md."
}
if (-not $Thumbprint) { throw "No certificate thumbprint. Run tools\make_cert.ps1 first." }
$cert = Get-ChildItem Cert:\CurrentUser\My | Where-Object { $_.Thumbprint -eq $Thumbprint } | Select-Object -First 1
if (-not $cert) { throw "The certificate $Thumbprint is not in Cert:\CurrentUser\My" }

$signtool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
if ($signtool) {
    $signArgs = @("sign", "/fd", "SHA256", "/sha1", $Thumbprint)
    if (-not $NoTimestamp) { $signArgs += @("/tr", $settings["timestamp_url"], "/td", "SHA256") }
    & $signtool.FullName @signArgs $Path
    if ($LASTEXITCODE -ne 0) { throw "SignTool failed. If the timestamp server can't be reached, rerun with -NoTimestamp." }
} else {
    $tsArgs = @{}
    if (-not $NoTimestamp) { $tsArgs["TimestampServer"] = $settings["timestamp_url"] }
    Set-AuthenticodeSignature -FilePath $Path -Certificate $cert -HashAlgorithm SHA256 @tsArgs | Out-Null
}
if ($NoTimestamp) { Write-Host "No timestamp: this signature stops being valid when the certificate expires." }

$sig = Get-AuthenticodeSignature -FilePath $Path
if ($sig.Status -in @("NotSigned", "HashMismatch")) { throw "Signature check failed: $($sig.Status)" }
if ($sig.SignerCertificate.Thumbprint -ne $Thumbprint) { throw "Signed with the wrong certificate" }
if ($sig.Status -ne "Valid") {
    Write-Host "Status $($sig.Status). Expected for a self-signed certificate this machine has not trusted. The thumbprint matches."
}

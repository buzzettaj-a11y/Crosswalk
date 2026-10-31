# Makes a self-signed code signing certificate (M14 section 5, docs/SIGNING.md).
# Source: Microsoft, New-SelfSignedCertificate (pki module). Not run in the cloud session.
param([switch]$Ci)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$settings = Get-Content (Join-Path $PSScriptRoot "signing.json") -Raw | ConvertFrom-Json
$local = Join-Path $PSScriptRoot "signing.local.json"

if ($Ci) {
    $subject = "CN=Wholecount CI (not for release)"
    $notAfter = (Get-Date).AddDays(1)
} else {
    $subject = "CN=$($settings.publisher)"
    $notAfter = (Get-Date).AddYears(3)
}
$cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject -KeyAlgorithm RSA -KeyLength 3072 `
    -HashAlgorithm SHA256 -KeyExportPolicy Exportable -CertStoreLocation Cert:\CurrentUser\My -NotAfter $notAfter
$cer = Join-Path $root "Output\wholecount-signing.cer"
New-Item -ItemType Directory -Force (Split-Path $cer) | Out-Null
Export-Certificate -Cert $cert -FilePath $cer | Out-Null

if ($Ci) {
    "thumbprint=$($cert.Thumbprint)" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    "cer=$cer" | Out-File -FilePath $env:GITHUB_OUTPUT -Append -Encoding utf8
    return
}
$answer = Read-Host "Save a .pfx backup of the private key? (y/n)"
if ($answer -eq "y") {
    $password = Read-Host "Password for the .pfx" -AsSecureString
    $pfx = Join-Path $HOME "Documents\wholecount-signing.pfx"
    Export-PfxCertificate -Cert $cert -FilePath $pfx -Password $password | Out-Null
    Write-Host "Backup written to $pfx. Keep it off the repository and off cloud sync."
}
$data = @{}
if (Test-Path $local) { $data = Get-Content $local -Raw | ConvertFrom-Json -AsHashtable }
$data["thumbprint"] = $cert.Thumbprint
$data | ConvertTo-Json | Set-Content $local -Encoding utf8
Write-Host "Certificate made for $subject, valid until $($notAfter.ToString('yyyy-MM-dd'))."
Write-Host "Thumbprint $($cert.Thumbprint) is saved in tools\signing.local.json."
Write-Host "Public certificate: $cer. Give this file to IT to trust, never the .pfx."

# Runs inside Windows Sandbox with networking off (M14 section 8). Writes one line per step to sandbox-result.txt.
$results = "C:\Wholecount\results"
$in = "C:\Wholecount\in"
$log = Join-Path $results "sandbox-result.txt"
function Step($name, $block) {
    try { & $block; Add-Content $log "$name ok" } catch { Add-Content $log "$name failed" }
}
Step "trust certificate" {
    $cer = Get-ChildItem $in -Filter *.cer | Select-Object -First 1
    Import-Certificate -FilePath $cer.FullName -CertStoreLocation Cert:\LocalMachine\Root | Out-Null
    Import-Certificate -FilePath $cer.FullName -CertStoreLocation Cert:\LocalMachine\TrustedPublisher | Out-Null
}
Step "install" {
    $setup = Get-ChildItem $in -Filter Wholecount-Setup-*.exe | Select-Object -First 1
    $p = Start-Process $setup.FullName -ArgumentList "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /LOG=`"$results\install.log`"" -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "installer exit $($p.ExitCode)" }
}
Step "self-check" {
    $exe = "$env:ProgramFiles\Wholecount\Wholecount.exe"
    $p = Start-Process $exe -ArgumentList "--self-check --self-check-out `"$results\selfcheck`"" -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "self-check exit $($p.ExitCode)" }
}
Step "start app" { Start-Process "$env:ProgramFiles\Wholecount\Wholecount.exe" }

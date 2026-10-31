# Builds dist\Wholecount and, unless -NoInstaller, the installer (M14). Run from the repository root in the activated .venv.
# Not run in the cloud session; the Windows job runs it. Nothing here downloads anything.
param([switch]$NoInstaller, [string]$Iscc = "", [string]$SignTool = "")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

python tools\make_version_info.py
python tools\make_icon.py
python tools\collect_licenses.py
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build build\wholecount.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
python tools\check_bundle.py dist\Wholecount build\wholecount
if ($LASTEXITCODE -ne 0) { throw "check_bundle found a problem" }
$env:WHOLECOUNT_DIST = (Resolve-Path dist\Wholecount).Path
$env:WHOLECOUNT_BUILD = (Resolve-Path build\wholecount).Path
python -m pytest -q tests\bundle
if ($LASTEXITCODE -ne 0) { throw "bundle tests failed" }

if ($NoInstaller) { return }
if (-not $Iscc) {
    $Iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Iscc) { throw "Inno Setup 6 (ISCC.exe) was not found" }
$version = python -c "from wholecount.brand import VERSION; print(VERSION)"
$publisher = python -c "import json,pathlib; d=json.load(open('tools/signing.json')); p=pathlib.Path('tools/signing.local.json'); d.update(json.load(open(p)) if p.exists() else {}); print(d['publisher'])"
$isccArgs = @("/DAppVersion=$version", "/DPublisher=$publisher")
if ($SignTool) { $isccArgs += @("/DSignIt", "/Swholecountsign=$SignTool") }
& $Iscc @isccArgs installer\wholecount.iss
if ($LASTEXITCODE -ne 0) { throw "ISCC failed" }

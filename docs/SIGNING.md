# Signing Wholecount

This page is for the maintainer. It covers making the certificate, signing a release, what CI signs with, and how to switch to Azure Artifact Signing later. Every command comes from the Microsoft page named beside it. Nothing here ran in the cloud session, so each step is marked Unconfirmed until the Windows checks pass.

## Make the certificate (once)

1. In PowerShell, from the repository folder, run `.\tools\make_cert.ps1`. It uses `New-SelfSignedCertificate` from Microsoft's "New-SelfSignedCertificate" page to make an RSA 3072, SHA-256 code signing certificate. Its subject is `CN=` plus the `publisher` setting in `tools/signing.json`, and it stays valid for three years in `Cert:\CurrentUser\My`. **Unconfirmed.**
2. It exports the public certificate to `Output\wholecount-signing.cer`. That file is the one IT staff trust. It's safe to share.
3. It offers to save a `.pfx` backup of the private key with a password. Keep that file off the repository and off cloud sync (OneDrive, Dropbox, Google Drive and Box). `.gitignore` already ignores `*.pfx` and `*.p12`.
4. It writes the thumbprint into `tools/signing.local.json`, which git ignores, and prints three lines to read.

## Sign a release

Run `.\tools\release.ps1` in the activated `.venv`. In order, it:

1. builds the app with `tools\build.ps1` (PyInstaller, the bundle check and the bundle tests)
2. signs `Wholecount.exe` with `tools\sign.ps1`
3. compiles the installer with Inno Setup, so the installer holds the signed exe
4. signs the installer, and prints the SHA-256 and the signature status of both files

`tools\sign.ps1` uses `signtool.exe` from the newest Windows SDK when there is one, following Microsoft's "SignTool" page. Without the SDK it falls back to `Set-AuthenticodeSignature`, from Microsoft's "Set-AuthenticodeSignature" page, so nothing extra has to be installed. It signs with SHA-256 and then checks the result with `Get-AuthenticodeSignature`. **Unconfirmed.**

## Timestamps

A timestamp keeps a signature valid after the certificate expires. The signing step asks the timestamp server in `tools/signing.json` for one. That is the only network use in signing: it happens on the maintainer's computer at build time, and never in the app. If the server can't be reached, signing fails. Rerun with `-NoTimestamp` to sign anyway, and the script says the signature stops being valid when the certificate expires.

## Renew before it expires

Make a new certificate with `make_cert.ps1` a month or so before the old one expires, send the new `.cer` to IT, and sign the next release with it. Releases signed with a timestamp stay valid.

## What CI signs with

The Windows workflow makes a new certificate in each run, named `Wholecount CI (not for release)` and valid for one day, with `make_cert.ps1 -Ci`. It never reads a secret, and the real key never leaves the maintainer's computer. The run uploads the CI `.cer` beside the installer, so it can be trusted for a test and then removed.

## Switching to Azure Artifact Signing

Azure Artifact Signing gives a publisher identity that SmartScreen builds a reputation for, without keeping a key file. It costs a monthly fee and has eligibility rules for the organization, so read SPEC section 14's note and Microsoft's "Artifact Signing" overview before deciding. Switching is a change to `tools/signing.json`: set `provider` to `azure_artifact_signing` and fill in the endpoint, account and profile names, which aren't secrets. The `azure_artifact_signing` branch in `tools\sign.ps1` is **Unconfirmed**, because nothing here could run it.

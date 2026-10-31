# Wholecount for IT staff

This page is for the IT staff who install Wholecount and decide whether to trust it. It says what the program does and doesn't do, which firewall rules it adds, how to check the installer, and where its data lives.

## What Wholecount does and doesn't do

- **It works on this computer only.** It reads client list files the operator chooses and writes only the files the operator downloads, into a folder they pick.
- **It connects to nothing.** The program has no network code. The build leaves out Python's and Qt's network modules, and a guard inside the program refuses any network call or network path while it runs. The installer adds two Windows Firewall rules that block `Wholecount.exe` in both directions.
- **It uses no AI of any kind.** No AI library, service or model file is in the program, and tests check the shipped folder for them.
- **It places addresses with Geosupport Desktop Edition** when that is installed on the same computer. Geosupport is a separate program from NYC Planning. Wholecount doesn't install it.

The program proves it can work with no network at all: a Windows Sandbox run with networking switched off installs it and runs it. That doesn't prove it could never use a network, which is why the firewall rules and the guard are there too.

## Supported systems

- Windows 10 version 22H2 and Windows 11, 64-bit only.
- The installer installs for all users and needs administrator approval.

## The publisher

The installer and `Wholecount.exe` are signed. The publisher name on the signature is the `publisher` setting in `tools/signing.json` in the source, which is "Joe Buzzetta" now. It can be changed to a business name before a release.

## The firewall rules

The installer adds two rules and the uninstaller removes them.

| Rule name | Program | Direction | Action | Profile |
| --- | --- | --- | --- | --- |
| Wholecount offline (out) | C:\Program Files\Wholecount\Wholecount.exe | Out | Block | Any |
| Wholecount offline (in) | C:\Program Files\Wholecount\Wholecount.exe | In | Block | Any |

These are the exact commands the installer runs, from Microsoft's "netsh advfirewall firewall" page:

```
netsh advfirewall firewall delete rule name="Wholecount offline (out)"
netsh advfirewall firewall delete rule name="Wholecount offline (in)"
netsh advfirewall firewall add rule name="Wholecount offline (out)" dir=out action=block program="C:\Program Files\Wholecount\Wholecount.exe" enable=yes profile=any
netsh advfirewall firewall add rule name="Wholecount offline (in)" dir=in action=block program="C:\Program Files\Wholecount\Wholecount.exe" enable=yes profile=any
```

For Group Policy or Intune, these PowerShell lines make the same rules. They come from Microsoft's "New-NetFirewallRule" and "Remove-NetFirewallRule" pages:

```
New-NetFirewallRule -DisplayName 'Wholecount offline (out)' -Direction Outbound -Action Block -Program 'C:\Program Files\Wholecount\Wholecount.exe' -Profile Any -Enabled True
New-NetFirewallRule -DisplayName 'Wholecount offline (in)' -Direction Inbound -Action Block -Program 'C:\Program Files\Wholecount\Wholecount.exe' -Profile Any -Enabled True
Remove-NetFirewallRule -DisplayName 'Wholecount offline (out)'
Remove-NetFirewallRule -DisplayName 'Wholecount offline (in)'
```

**Unconfirmed:** whether the name `netsh` gives a rule is the same as PowerShell's `DisplayName`. The Windows tests check this.

If your Group Policy turns off local rule merging, Windows ignores rules the installer adds on the computer itself. In that case, deploy the two rules above through Group Policy or Intune instead. That comes from Microsoft's "Windows Firewall rules" guidance on rule merging.

If the installer can't add the rules, its last page says so, and the install log records it. Wholecount still runs, but Windows won't block it from the network.

## Checking the installer

1. Compare the file's hash with the one published beside it. From Microsoft's "Get-FileHash" page:

   ```
   Get-FileHash .\Wholecount-Setup-<version>.exe -Algorithm SHA256
   ```

2. Check the signature. From Microsoft's "Get-AuthenticodeSignature" page:

   ```
   Get-AuthenticodeSignature .\Wholecount-Setup-<version>.exe | Format-List Status, SignerCertificate
   ```

   The signer's subject names the publisher, and its thumbprint should match the one you were given. Before the certificate is trusted, the status is `UnknownError` or `NotTrusted`. After it's trusted, it is `Valid`.

## Trusting the certificate

The certificate is self-signed, so Windows doesn't trust it until you tell it to. Put the public `.cer` file in two stores: Trusted Root Certification Authorities and Trusted Publishers. Never ask for the private key.

- **Group Policy.** Computer Configuration, Windows Settings, Security Settings, Public Key Policies, then import the `.cer` under Trusted Root Certification Authorities and under Trusted Publishers. That comes from Microsoft's "Distribute certificates to client computers by using Group Policy" page.
- **Intune.** Use a trusted certificate profile for each store. That comes from Microsoft's "Trusted root certificate profiles" page.
- **One computer.** From an administrator prompt, using Microsoft's "certutil" page:

  ```
  certutil -addstore Root wholecount-signing.cer
  certutil -addstore TrustedPublisher wholecount-signing.cer
  ```

To allow Wholecount through AppLocker or App Control for Business, add a publisher rule for the certificate's subject. That comes from Microsoft's "Understanding AppLocker rule condition types" and App Control's signer rule pages.

**SmartScreen and Smart App Control.** On a computer that hasn't trusted the certificate, SmartScreen warns before the installer runs, and Smart App Control may block it. Those warnings stay on unmanaged computers. Whether they accept the certificate once it is trusted by policy is to confirm on a managed machine.

## Where data lives

Wholecount keeps its own files in `%LOCALAPPDATA%\Wholecount` for each Windows user. None of them leaves the computer.

| File or folder | What it is |
| --- | --- |
| `key.bin` | The install secret, encrypted with Windows Data Protection for this user. It keys every record and person key. |
| `prefs.json` | Settings only: whether progress is saved and the matching lines. No client data. |
| `sessions\` | Saved progress, encrypted. It holds the set-up and the decisions, never cell values. |
| `setups\` | Saved set-ups, which hold column choices and no client data. |
| `crosswalk.db` | The saved crosswalk, only when the organization turns it on. It holds keyed hashes, master IDs and decisions, never names, addresses, IDs or dates. |
| `calibration\` | Matching labels, encrypted, only after staff measure matching. They hold keyed hashes and labels, never client values. |
| `reference\` | An address reference file, only if one was added. |

`key.bin` is the install secret. If it is deleted, saved progress and a saved crosswalk can't be read again. Settings in the program can back it up to a file protected with a passphrase, and restore it.

**Removing everything.** Uninstall Wholecount from Settings, Apps. That removes the program and the two firewall rules. Then delete `%LOCALAPPDATA%\Wholecount` for each user who used it. The uninstaller leaves that folder in place and says so, because it can't know every user. Files people downloaded stay where they saved them.

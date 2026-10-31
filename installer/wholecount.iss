; Wholecount installer (M14 section 4, Inno Setup 6, research R5).
; Compiled by tools/build.ps1 and tools/release.ps1 with /DAppVersion=... /DPublisher=... and, when signing, /DSignIt.
; Not compiled in the cloud session. Lines the research marks Unconfirmed are checked by the Windows job.

#ifndef AppVersion
  #error AppVersion must be passed with /DAppVersion
#endif
#ifndef Publisher
  #define Publisher "Joe Buzzetta"
#endif

[Setup]
; Made once for M14 and never changed, so an upgrade finds the earlier install.
AppId={{AF8BB1F2-7D46-44B0-8243-48004766D781}
AppName=Wholecount
AppVersion={#AppVersion}
AppPublisher={#Publisher}
PrivilegesRequired=admin
DefaultDirName={autopf}\Wholecount
; 64-bit only. Unconfirmed in the research: the accepted value name, so the Windows job is the arbiter.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Windows 10 22H2 or later (SPEC 14).
MinVersion=10.0.19045
; Restart Manager closes a running Wholecount and nothing else (A-17).
CloseApplications=yes
OutputDir=..\Output
OutputBaseFilename=Wholecount-Setup-{#AppVersion}
UninstallDisplayIcon={app}\Wholecount.exe
DisableProgramGroupPage=yes
Compression=lzma2
SolidCompression=yes
#ifdef SignIt
SignTool=wholecountsign
SignedUninstaller=yes
#endif

[Messages]
WelcomeLabel2=Wholecount works on this computer only. This setup adds two Windows Firewall rules that block Wholecount.exe from using the network in either direction. It connects to nothing and downloads nothing.

[InstallDelete]
; An upgrade never leaves a module the new build dropped.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\Wholecount\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Wholecount"; Filename: "{app}\Wholecount.exe"

[Run]
; Remove leftovers from an earlier install first (a missing rule makes this fail harmlessly), then add both directions.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Wholecount offline (out)"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Wholecount offline (in)"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""Wholecount offline (out)"" dir=out action=block program=""{app}\Wholecount.exe"" enable=yes profile=any"; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""Wholecount offline (in)"" dir=in action=block program=""{app}\Wholecount.exe"" enable=yes profile=any"; Flags: runhidden waituntilterminated
; The app never starts with the installer's administrator token.
Filename: "{app}\Wholecount.exe"; Description: "Launch Wholecount"; Flags: postinstall nowait skipifsilent runasoriginaluser

[UninstallRun]
; Delete by name, not by program, so the order relative to file removal does not matter.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Wholecount offline (out)"""; Flags: runhidden; RunOnceId: "DelFwOut"
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Wholecount offline (in)"""; Flags: runhidden; RunOnceId: "DelFwIn"

[Code]
var
  GeoPage: TOutputMsgWizardPage;

{ Follows M05's discover_geosupport_dirs: the folder above GEOFILES (machine, then user), then the two standard folders.
  GEOFILES set to an empty value means Geosupport is turned off, so nothing is found. }
function GeofilesValue(var Value: String): Boolean;
begin
  Result := RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'GEOFILES', Value);
  if not Result then
    Result := RegQueryStringValue(HKCU, 'Environment', 'GEOFILES', Value);
end;

function GeosupportFound(): Boolean;
var
  Geofiles: String;
begin
  Result := False;
  if GeofilesValue(Geofiles) then
  begin
    if Trim(Geofiles) = '' then
      exit;
    if DirExists(ExtractFileDir(RemoveBackslashUnlessRoot(Trim(Geofiles)))) then
      Result := True;
  end;
  if not Result then
    Result := DirExists('C:\Program Files\Geosupport Desktop Edition') or
              DirExists('C:\Program Files (x86)\Geosupport Desktop Edition');
  if Result then
    Log('Geosupport check: found')
  else
    Log('Geosupport check: not found');
end;

procedure InitializeWizard();
begin
  if not GeosupportFound() then
    GeoPage := CreateOutputMsgPage(wpWelcome, 'Geosupport Desktop Edition',
      'Placing addresses',
      'Geosupport Desktop Edition was not found on this computer. Wholecount will install and run, but it cannot place addresses until Geosupport is installed or you add an address reference file. You can do either later.');
end;

function RuleExists(const Name: String): Boolean;
var
  Code: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\netsh.exe'), 'advfirewall firewall show rule name="' + Name + '"', '',
                 SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
  begin
    if not (RuleExists('Wholecount offline (out)') and RuleExists('Wholecount offline (in)')) then
    begin
      Log('Firewall rules: missing');
      WizardForm.FinishedLabel.Caption := 'The firewall rules could not be added. Wholecount will still run, but Windows will not block it from using the network. See IT_TRUST.md.';
    end
    else
      Log('Firewall rules: present');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    SuppressibleMsgBox('Saved progress, settings and the install secret in %LOCALAPPDATA%\Wholecount were left in place. Delete that folder to remove them. A saved crosswalk can''t be read without the install secret.',
      mbInformation, MB_OK, IDOK);
end;

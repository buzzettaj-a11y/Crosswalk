' Stop Crosswalk. Double-click this if the tool is still running after the
' browser was closed, for example before deleting or replacing this folder.
' It asks the tool to stop politely first, then ends the process if it must.

Option Explicit
Dim shell, fso, here, http, stopped, pidPath, pid, f

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
stopped = False

' 1) ask nicely on the usual port
On Error Resume Next
Set http = CreateObject("MSXML2.XMLHTTP")
http.Open "POST", "http://127.0.0.1:8765/api/quit", False
http.Send "{}"
If Err.Number = 0 And http.Status = 200 Then stopped = True
Err.Clear
On Error GoTo 0

' 2) otherwise end the process recorded when it started
pidPath = here & "\crosswalk.pid"
If Not stopped And fso.FileExists(pidPath) Then
  Set f = fso.OpenTextFile(pidPath, 1)
  pid = Trim(f.ReadLine)
  f.Close
  shell.Run "taskkill /PID " & pid & " /F", 0, True
  stopped = True
End If

' 3) last resort: any pythonw running launch.py from this folder
If Not stopped Then
  shell.Run "cmd /c wmic process where ""name='pythonw.exe' and commandline like '%launch.py%'"" call terminate", 0, True
  stopped = True
End If

If fso.FileExists(pidPath) Then fso.DeleteFile pidPath, True
MsgBox "Crosswalk has been stopped. This folder can now be moved, replaced or deleted.", vbInformation, "Crosswalk"

' Crosswalk. Double-click this file to start the tool.
' It runs without a black command window. If Python is not installed, it says
' so in plain words rather than failing silently.

Option Explicit
Dim shell, fso, here, pyw, py, cmd, found

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = here

' pythonw runs without a console window, which is what we want.
found = False
On Error Resume Next
shell.Run "pythonw.exe -c ""import sys""", 0, True
If Err.Number = 0 Then found = True
Err.Clear
On Error GoTo 0

If Not found Then
  ' Fall back to python.exe, still hidden.
  On Error Resume Next
  shell.Run "python.exe -c ""import sys""", 0, True
  If Err.Number = 0 Then
    found = True
    pyw = "python.exe"
  End If
  Err.Clear
  On Error GoTo 0
Else
  pyw = "pythonw.exe"
End If

If Not found Then
  MsgBox "Crosswalk needs Python, and it is not installed on this computer." & vbCrLf & vbCrLf & _
         "Install it once from python.org/downloads." & vbCrLf & _
         "During setup, tick the box that says 'Add python.exe to PATH'." & vbCrLf & vbCrLf & _
         "Then double-click Crosswalk again.", _
         vbExclamation, "Crosswalk cannot start"
  WScript.Quit 1
End If

' Start the tool. It opens the browser itself once it is ready.
shell.Run """" & pyw & """ """ & here & "\launch.py""", 0, False

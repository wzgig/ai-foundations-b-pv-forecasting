Option Explicit

Dim shell, fso, scriptDir, launcher, command

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = scriptDir & "\software_launcher.py"

If Not fso.FileExists(launcher) Then
    MsgBox "Cannot find software_launcher.py in: " & scriptDir, vbCritical, "PV Forecasting Launcher"
    WScript.Quit 1
End If

shell.CurrentDirectory = scriptDir

On Error Resume Next
command = "pythonw.exe " & Chr(34) & launcher & Chr(34)
shell.Run command, 1, False

If Err.Number <> 0 Then
    Err.Clear
    command = "python.exe " & Chr(34) & launcher & Chr(34)
    shell.Run command, 1, False
End If

If Err.Number <> 0 Then
    MsgBox "Cannot start Python. Please install Python 3.12 or run run.bat for diagnostics.", vbCritical, "PV Forecasting Launcher"
    WScript.Quit 1
End If

On Error GoTo 0

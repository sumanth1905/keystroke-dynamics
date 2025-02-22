Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")
scriptDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Launch all required scripts
objShell.Run "pythonw.exe """ & scriptDir & "\iot_monitor.py""", 0, False
objShell.Run "pythonw.exe """ & scriptDir & "\check_unlock.py""", 0, False
objShell.Run "pythonw.exe """ & scriptDir & "\lockscreen.py""", 0, False

Set objShell = Nothing
Set objFSO = Nothing
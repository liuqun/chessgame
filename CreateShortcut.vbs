pathToPythonwExe = "C:\Panda3D-1.9.4-x64\python\pythonw.exe"
pathToMainPy = "main.py"

set WshShell = WScript.CreateObject("WScript.Shell")
set oShellLink = WshShell.CreateShortcut("View Chessborad.lnk")
oShellLink.TargetPath = pathToPythonwExe
oShellLink.Arguments = "-E " & pathToMainPy
oShellLink.WindowStyle = 1
oShellLink.Hotkey = ""
oShellLink.IconLocation = "cmd.exe, 0"
oShellLink.Description = ""
oShellLink.WorkingDirectory = ""
oShellLink.Save

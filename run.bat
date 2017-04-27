@echo off
rem Note:
rem This program needs Panda3D SDK, which can be downloaded from:
rem https://www.panda3d.org/download.php?sdk&version=1.9.4
rem Install the SDK into the default directory, which is at:
rem C:\Panda3D-1.9.4-x64

@echo Creating shortcut...
cscript//nologo CreateShortcut.vbs

@echo To run the program later, you can also click this shortcut:
@echo on
"View Chessborad.lnk"
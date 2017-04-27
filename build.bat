@echo on

set PANDA_DIR=C:\Panda3D-1.9.4-x64

set BUILD_NAME=Chess
set VERSION=alpha
set BUILD_ROOT=%BUILD_NAME%-%VERSION%

md %BUILD_ROOT%
xcopy/Y *.py %BUILD_ROOT%

md %BUILD_ROOT%\models
xcopy/Y/S models %BUILD_ROOT%\models

mkdir %BUILD_ROOT%\Pmw
xcopy/Y/S %PANDA_DIR%\Pmw %BUILD_ROOT%\Pmw

%PANDA_DIR%\bin\packpanda.exe --dir %BUILD_ROOT% --name ChessboardGame
@echo Package %BUILD_ROOT%.exe has been built.
@pause
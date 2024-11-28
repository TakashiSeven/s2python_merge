@echo off
cd /d "%~dp0"

if exist "%~dp0repak.exe" (
    set "tool=repak.exe"
) else (
    if exist "C:\Program Files\repak_cli\bin\repak.exe" (
        set "tool=C:\Program Files\repak_cli\bin\repak.exe"
    ) else (
        echo Error: repak.exe isn't found.
        echo Please ensure it is installed or present at script's location.
        pause
        exit /b 1
    )
)

"%tool%" unpack "%~1"
tree "%~dpn1" /f /a | findstr /v "Volume Folder"
pause

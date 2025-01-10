@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title PAK Conflict Analyzer [Windows 11]

:: Set colors for output and enable virtual terminal sequences
color 0b
reg add HKEY_CURRENT_USER\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

:: Store the script's directory and set target mods directory
set "SCRIPT_DIR=%~dp0"

:: python script should be in the same folder as this bat file
set "PYTHON_SCRIPT=%SCRIPT_DIR%1_Python_Merging_s2hoc.py"

:: location of your mods folder
set "MODS_DIR=E:\s2hoc\Stalker2\Content\Paks\~mods"

:: Clear screen
cls

echo [92m╔════════════════════════╗
echo ║  PAK Conflict Analyzer  ║
echo ╚════════════════════════╝[0m
echo.

:: Validate if Python script exists
if not exist "%PYTHON_SCRIPT%" (
    color 0c
    echo [91m ERROR: Cannot find the Python script at:[0m
    echo %PYTHON_SCRIPT%
    echo.
    echo Please ensure the batch file is in the same directory as the Python script.
    echo.
    pause
    exit /b 1
)

:: Validate if mods directory exists
if not exist "%MODS_DIR%" (
    color 0c
    echo [91m ERROR: Mods directory not found at:[0m
    echo %MODS_DIR%
    echo.
    pause
    exit /b 1
)

:: Initialize variables
set "VALID_FILES="
set "FILE_COUNT=0"

echo [96mScanning for .pak files in:[0m
echo %MODS_DIR%
echo and its subfolders...
echo.

:: Find all .pak files recursively
for /r "%MODS_DIR%" %%F in (*.pak) do (
    set /a FILE_COUNT+=1
    set "VALID_FILES=!VALID_FILES! "%%~fF""
    echo [90m⚬ Found:[0m %%~nxF
)

:: Check if we found any .pak files
if %FILE_COUNT% equ 0 (
    color 0c
    echo [91m ERROR: No .pak files found in the mods directory.[0m
    echo.
    pause
    exit /b 1
)

:: Try to locate Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    where py >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        color 0c
        echo [91m ERROR: Python is not found in the system PATH[0m
        echo Please install Python and ensure it's added to the system PATH
        echo.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py"
) else (
    set "PYTHON_CMD=python"
)

:: Display summary
color 0a
echo.
echo [92m Found %FILE_COUNT% .pak files to analyze [0m
echo.
echo [93m Starting conflict analysis...[0m
echo [90m This will NOT merge any files - analysis only mode[0m
echo.

:: Execute the Python script with the analyze flag
%PYTHON_CMD% "%PYTHON_SCRIPT%" --analyze %VALID_FILES%

:: Check if Python script execution had an error
if %ERRORLEVEL% neq 0 (
    color 0c
    echo.
    echo [91m ERROR: The conflict analysis encountered an error.[0m
    echo.
    pause
    exit /b 1
)

:: Normal exit
echo.
echo [92m✓ Analysis complete![0m
pause
exit /b 0

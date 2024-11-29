@echo off
setlocal EnableDelayedExpansion
title Mod Merger Launcher

:: Set colors for output
color 0b

:: Store the script's directory
set "SCRIPT_DIR=%~dp0"
set "PYTHON_SCRIPT=%SCRIPT_DIR%1_Python_Merging_s2hoc.py"

:: Clear screen
cls

echo Mod Merger Launcher
echo =================
echo.

:: Validate if Python script exists
if not exist "%PYTHON_SCRIPT%" (
    color 0c
    echo ERROR: Cannot find the Python script at:
    echo %PYTHON_SCRIPT%
    echo.
    echo Please ensure the batch file is in the same directory as the Python script.
    echo.
    pause
    exit /b 1
)

:: Check if any files were dropped
if "%~1"=="" (
    echo Usage: Drag and drop .pak files onto this batch file
    echo.
    pause
    exit /b 1
)

:: Initialize variables
set "VALID_FILES="
set "INVALID_FILES="
set "FILE_COUNT=0"

:: Validate all dropped files
for %%F in (%*) do (
    set /a FILE_COUNT+=1
    if /i "%%~xF"==".pak" (
        set "VALID_FILES=!VALID_FILES! "%%~fF""
    ) else (
        set "INVALID_FILES=!INVALID_FILES! %%~nxF"
    )
)

:: Check for invalid files
if not "!INVALID_FILES!"=="" (
    color 0e
    echo Warning: The following files are not .pak files and will be ignored:
    echo !INVALID_FILES!
    echo.
    timeout /t 3 >nul
)

:: Check if we have any valid files to process
if "!VALID_FILES!"=="" (
    color 0c
    echo ERROR: No valid .pak files were provided.
    echo Please drag and drop .pak files only.
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
        echo ERROR: Python is not found in the system PATH
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
echo Found !FILE_COUNT! files to process
echo.
echo Starting merge process...
echo.

:: Execute the Python script with the valid files
%PYTHON_CMD% "%PYTHON_SCRIPT%" %VALID_FILES%

:: Check if Python script execution had an error
if %ERRORLEVEL% neq 0 (
    color 0c
    echo.
    echo ERROR: The Python script encountered an error.
    echo.
    pause
    exit /b 1
)

:: Normal exit - no need to pause since Python script has its own exit prompt
exit /b 0

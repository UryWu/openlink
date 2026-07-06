@echo off
:: ============================================================
::  Script Name : kill_backend_server_via_port_39527.bat
::  Description : Find and kill the process occupying port 39527
::  Use Case    : Quickly release a occupied port during dev
::  Usage       : Right-click -> Run as administrator
::  Note        : Cannot kill System (PID=4) owned processes
:: ============================================================

:: Enable delayed expansion to use !variable! inside parentheses
setlocal enabledelayedexpansion

:: ============================================================
::  Step 1: Find the PID of the process listening on port 39527
::  netstat -aon        : Show all connections with PID
::  findstr :39527      : Filter lines containing ":39527"
::  findstr LISTENING   : Filter only LISTENING state
::  tokens=5            : Extract the 5th column (PID column)
::  Store the result into variable PID
:: ============================================================
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :39527 ^| findstr LISTENING') do (
    set PID=%%a
)

:: ============================================================
::  Step 2: Check if any process was found on the port
::  If PID is empty, no process is using the port
:: ============================================================
if not defined PID (
    echo No process found on port 39527.
    pause
    exit /b
)

:: ============================================================
::  Step 3: Display process information for the found PID
::  !PID! uses exclamation marks due to delayed expansion
::  tasklist shows the process name and resource usage
::  2>nul redirects error output (e.g., process not found)
:: ============================================================
echo Found PID: !PID!
echo.
tasklist /FI "PID eq !PID!" 2>nul

:: ============================================================
::  Step 4: Prompt for confirmation to prevent accidental kills
::  set /p asks the user to enter Y or N
::  /i makes the comparison case-insensitive (Y or y both work)
:: ============================================================
echo.
set /p confirm=Kill this process? (Y/N): 

:: ============================================================
::  Step 5: Evaluate user input
::  If user did NOT enter Y (or y), cancel and exit
:: ============================================================
if /i not "!confirm!"=="Y" (
    echo Cancelled.
    pause
    exit /b
)

:: ============================================================
::  Step 6: Forcefully terminate the process
::  taskkill /F    : Force termination
::  /PID !PID!     : Specify the process ID to kill
::  errorlevel will be set after execution
:: ============================================================
taskkill /F /PID !PID!

:: ============================================================
::  Step 7: Check if termination was successful
::  errorlevel = 0  : Success
::  errorlevel != 0 : Failed (permission denied, process gone, etc.)
:: ============================================================
if !errorlevel! equ 0 (
    echo Success!
) else (
    echo Failed, please run as administrator.
)

:: ============================================================
::  Pause so the user can see the result before the window closes
:: ============================================================
pause
@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0" || exit /b 1
echo.
echo Starting Floorpy... Leave this window open, closing it could prevent cleaning temporary files.

cd Floorp || (
    echo Error: 'Floorp' directory not found.
    pause
    exit /b 1
)

Floorp.exe -profile TempProfile || (
    echo Error: Could not launch Floorp.exe. Please ensure Floorp.exe is in the 'Floorp' directory.
    pause
    exit /b 1
)

:: Wait for browser to initialize and lock its profile
ping 127.0.0.1 -n 3 >nul

:waitloop
ping 127.0.0.1 -n 2 >nul
if exist "TempProfile\parent.lock" (
    :: Attempt to delete it to see if it is still locked by an active process
    del "TempProfile\parent.lock" >nul 2>&1
    if exist "TempProfile\parent.lock" goto waitloop
)

echo.
echo Floorpy closed.
echo.
echo If this window doesn't close automatically you may need to force close it.
echo.

call :validatecleanup
if errorlevel 1 (
    echo Warning: Script is not running from a temporary location. Skipping temporary file cleanup.
    pause
    exit /b 0
)

echo Cleaning temporary files...
cd /d "%CLEANUP_TEMP%" || exit /b 1
ping 127.0.0.1 -n 2 >nul
:: Read the remaining commands before deleting this batch file with its folder.
(
    rmdir /s /q "%CLEANUP_DIR%"
    if exist "%CLEANUP_DIR%\" (
        echo Warning: Could not remove all temporary files.
        exit /b 1
    )
    echo Done.
    ping 127.0.0.1 -n 2 >nul
    exit 0
)

:validatecleanup
:: Only delete a strict descendant of TEMP, never TEMP itself or a prefix match.
if not defined TEMP exit /b 1
for %%I in ("%TEMP%\.") do set "CLEANUP_TEMP=%%~fI"
for %%I in ("%~dp0.") do set "CLEANUP_DIR=%%~fI"
if not exist "%CLEANUP_TEMP%\" exit /b 1
if /I "%CLEANUP_DIR%"=="%CLEANUP_TEMP%" exit /b 1

set "CLEANUP_CANDIDATE=%CLEANUP_DIR%"
:cleanupancestor
:: A junction or symbolic link could redirect deletion outside the checked tree.
for %%I in ("%CLEANUP_CANDIDATE%") do set "CLEANUP_ATTRIBUTES=%%~aI"
if not defined CLEANUP_ATTRIBUTES exit /b 1
if not "%CLEANUP_ATTRIBUTES:l=%"=="%CLEANUP_ATTRIBUTES%" exit /b 1
if /I "%CLEANUP_CANDIDATE%"=="%CLEANUP_TEMP%" exit /b 0

set "CLEANUP_CHILD=%CLEANUP_CANDIDATE%"
for %%I in ("%CLEANUP_CHILD%\..") do set "CLEANUP_CANDIDATE=%%~fI"
if /I "%CLEANUP_CANDIDATE%"=="%CLEANUP_CHILD%" exit /b 1
goto cleanupancestor

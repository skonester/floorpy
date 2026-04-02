@echo off
cd /d "%~dp0"
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

REM Exit if the script isn't in %temp%
echo "%~dp0" | findstr /I /C:"%temp%" >nul 2>&1
if errorlevel 1 (
    echo Warning: Script is not running from a temporary location. Skipping temporary file cleanup.
    pause
    exit /b 0
)

echo Cleaning temporary files...
cd /d "%temp%"
ping 127.0.0.1 -n 2 >nul
rmdir /s /q "%~dp0"
echo Done.
ping 127.0.0.1 -n 2 >nul
exit
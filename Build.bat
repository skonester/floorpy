@echo off
cd /d "%~dp0"
setlocal enabledelayedexpansion

:: Dynamic paths relative to the script's root directory
set "inputfolder=%~dp0floorp"
set "archive=%~dp0floorp.7z"
set "outputexe=%~dp0floorpy.exe"

:: Localized tool dependencies
set "ResourceHackerPath=%~dp0ResourceHacker.exe"
set "7zPath=%~dp07za64.exe"
set "sfxPath=%~dp07zS264.sfx"

:main
echo.
echo.
echo Steps:
echo 1. Debloat %inputfolder%
echo 2. Pack %inputfolder% to %archive%
echo 3. Create %outputexe% using SFX
echo 4. Add icon and fix manifest (requires Resource Hacker)
echo.
echo F. Do steps 1, 2, 3, and 4 automatically
echo.
choice /C 1234F /N /M "Build Option:"
goto buildinput%errorlevel%

:buildinput1
cls
call :debloat
goto main
:buildinput2
cls
call :pack
goto main
:buildinput3
cls
call :makesfx
goto main
:buildinput4
cls
call :resourcehack
goto main
:buildinput5
cls
call :debloat
call :pack
call :makesfx
call :resourcehack
goto done

:debloat
echo.
echo Debloating "%inputfolder%"...
pushd "%inputfolder%" || (echo Error: "%inputfolder%" directory not found. Exiting debloat. & exit /b 1)

:: --- Directory removals ---
:: 'defaults' retained. Required for channel-prefs.js and Content Process sandboxing.
echo Removing unnecessary directories...
for %%d in (extensions fonts isp uninstall TempProfile) do (
    if exist "%%d" (
        rmdir /s /q "%%d"
        if exist "%%d" (echo Warning: Could not remove "%%d". It might be in use or protected.)
    ) else (
        echo Info: "%%d" directory not found, skipping.
    )
)

:: --- File removals ---
:: crashreporter.exe, minidump-analyzer.exe, and d3dcompiler_47.dll retained for media stability.
echo Removing unnecessary files...
for %%f in (updater.exe install.log blocklist.xml) do (
    if exist "%%f" (
        del /q "%%f"
        if exist "%%f" (echo Warning: Could not remove "%%f". It might be in use or protected.)
    ) else (
        echo Info: "%%f" file not found, skipping.
    )
)

popd
echo.
echo Copying TempProfile...
if exist "TempProfile\" (
    xcopy /E /I /Y "TempProfile\" "%inputfolder%\TempProfile\"
) else (
    echo Warning: "TempProfile\" directory not found in root. Skipping profile copy.
)

echo.
echo Debloat done. Please check the output for errors before continuing.
echo.
exit /B 0

:pack
echo.
echo Packing "%inputfolder%"...
call :find7z || (echo Error: 7za64.exe not found. Cannot pack. Exiting pack. & exit /b 1)

del /q "%archive%" >nul 2>&1
"!7zPath!" a -mx=9 "%archive%" "%inputfolder%" "%~dp0run.bat"
del /q exe.txt >nul 2>&1
echo.
echo Packing done. Please check the output for errors before continuing.
echo.
exit /B 0

:packfast
echo.
echo Fast Packing "%inputfolder%"...
call :find7z || (echo Error: 7za64.exe not found. Cannot fast pack. Exiting packfast. & exit /b 1)

del /q "%archive%" >nul 2>&1
"!7zPath!" a -mx=1 "%archive%" "%inputfolder%" "%~dp0run.bat"
del /q exe.txt >nul 2>&1
echo.
echo Fast Packing done. Please check the output for errors before continuing.
echo.
exit /B 0

:makesfx
echo.
echo Creating SFX executable...
if not exist "%sfxPath%" (
    echo Error: 7zS264.sfx not found in root. Cannot create SFX. Exiting makesfx.
    exit /b 1
)
if not exist "%archive%" (
    echo Error: "%archive%" archive not found. Please run 'Pack' first. Exiting makesfx.
    exit /b 1
)

del /q "%outputexe%" >nul 2>&1
copy /Y /b "%sfxPath%" + "%archive%" "%outputexe%"
echo.
echo SFX step done. Please check the output for errors before continuing.
echo.
exit /B 0

:resourcehack
echo.
echo Looking for Resource Hacker.exe...
set "rhpath="
set "RH1=%ProgramFiles(x86)%\Resource Hacker\ResourceHacker.exe"
set "RH2=%ProgramFiles%\Resource Hacker\ResourceHacker.exe"

echo    %ResourceHackerPath%
echo    %RH1%
echo    %RH2%
echo.

if exist "%ResourceHackerPath%" (
    set "rhpath=%ResourceHackerPath%"
) else if exist "%RH1%" (
    set "rhpath=%RH1%"
) else if exist "%RH2%" (
    set "rhpath=%RH2%"
)

if defined rhpath (
    echo Found: !rhpath!
    if not exist "%outputexe%" (
        echo Error: "%outputexe%" not found. Please run 'Make SFX' first. Exiting resourcehack.
        exit /b 1
    )
    if not exist "%~dp0icon.ico" (
        echo Error: icon.ico not found in root. Cannot add icon. Exiting resourcehack.
        exit /b 1
    )
    if not exist "%~dp0Manifest.txt" (
        echo Error: Manifest.txt not found in root. Cannot update manifest. Exiting resourcehack.
        exit /b 1
    )

    echo Adding icon...
    "!rhpath!" -open "%outputexe%" -save "%outputexe%" -action addoverwrite -resource "%~dp0icon.ico" -mask ICONGROUP,MAINICON,0 -log CONSOLE
    echo Updating manifest...
    "!rhpath!" -open "%outputexe%" -save "%outputexe%" -action addoverwrite -resource "%~dp0Manifest.txt" -mask Manifest,1, -log CONSOLE
    echo.
    echo Icon and manifest updated. Please check the output for errors before continuing.
    echo.
) else (
    echo Error: ResourceHacker.exe not found. Skipping icon and manifest update.
    pause
    exit /B 1
)
exit /B 0

:find7z
    echo DEBUG: Entering find7z. 7zPath is: "!7zPath!"

    if defined 7zPath (
        echo DEBUG: 7zPath is defined. Value: "!7zPath!"
        if exist "!7zPath!" (
            echo DEBUG: 7zPath exists. Exiting find7z successfully.
            exit /B 0
        ) else (
            echo DEBUG: 7zPath defined but file does NOT exist: "!7zPath!"
            set "7zPath="
        )
    )

    set "progfiles7z=%ProgramFiles%\7-Zip\7za.exe"
    set "progfilesx867z=%ProgramFiles(x86)%\7-Zip\7za.exe"

    echo DEBUG: Attempting to auto-detect 7za64.exe.

    if exist "%progfiles7z%" (
        set "7zPath=%progfiles7z%"
    ) else if exist "%progfilesx867z%" (
        set "7zPath=%progfilesx867z%"
    )

    if defined 7zPath (
        echo DEBUG: 7za.exe found at fallback: !7zPath!
        exit /B 0
    ) else (
        echo DEBUG: 7za64.exe not found during auto-detection.
        echo Error: 7za64.exe not found in root or common locations.
        exit /B 1
    )

:done
echo.
echo All steps completed.
pause
exit
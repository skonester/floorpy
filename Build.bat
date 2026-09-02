@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

set "ROOT=%~dp0"
set "INPUT_DIR=%ROOT%floorp"
set "BUILD_DIR=%ROOT%.build"
set "DOWNLOAD_DIR=%BUILD_DIR%\downloads"
set "EXTRACT_DIR=%BUILD_DIR%\floorp-extract"
set "ARCHIVE=%ROOT%floorp.7z"
set "OUTPUT_EXE=%ROOT%floorpy.exe"
set "RUN_SCRIPT=%ROOT%run.bat"
set "SFX_MODULE=%ROOT%7zS264.sfx"
set "ROOT_7Z=%ROOT%7za64.exe"
set "ROOT_RH=%ROOT%ResourceHacker.exe"
set "FLOORP_URL=https://github.com/Floorp-Projects/Floorp/releases/latest/download/floorp-windows-x86_64.installer.exe"
set "FLOORP_LEGACY_URL=https://github.com/Floorp-Projects/Floorp/releases/latest/download/floorp-win64.installer.exe"
set "FLOORP_INSTALLER=%DOWNLOAD_DIR%\floorp-win64.installer.exe"

:menu
echo.
echo Floorpy build
echo.
echo 1. Download latest Floorp into floorp\
echo 2. Pack floorp\ and run.bat into floorp.7z
echo 3. Create floorpy.exe from the SFX module
echo 4. Add icon and manifest with Resource Hacker
echo.
echo F. Build from the current floorp\ folder
echo U. Update Floorp, then build
echo Q. Quit
echo.
choice /C 1234FUQ /N /M "Build option: "
if errorlevel 7 goto done
if errorlevel 6 goto updatebuild
if errorlevel 5 goto localbuild
if errorlevel 4 call :resourcehack
if errorlevel 3 call :makesfx
if errorlevel 2 call :pack
if errorlevel 1 call :downloadfloorp
goto menu

:localbuild
call :pack || goto failed
call :makesfx || goto failed
call :resourcehack || goto failed
goto success

:updatebuild
call :downloadfloorp || goto failed
call :pack || goto failed
call :makesfx || goto failed
call :resourcehack || goto failed
goto success

:downloadfloorp
echo.
echo Downloading latest Floorp for Windows x64...
call :find7z || exit /b 1
call :ensurepowershell || exit /b 1

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
if not exist "%DOWNLOAD_DIR%" mkdir "%DOWNLOAD_DIR%"

call :downloadinstaller || exit /b 1

if exist "%EXTRACT_DIR%" rmdir /s /q "%EXTRACT_DIR%"
mkdir "%EXTRACT_DIR%" || exit /b 1

echo Extracting Floorp installer...
"%SEVEN_ZIP%" x "%FLOORP_INSTALLER%" -o"%EXTRACT_DIR%" -y -ir!core\*
if errorlevel 1 (
    echo Error: 7-Zip could not extract the Floorp installer.
    exit /b 1
)

if not exist "%EXTRACT_DIR%\core\floorp.exe" (
    echo Error: extracted installer did not contain core\floorp.exe.
    exit /b 1
)

if exist "%INPUT_DIR%.previous" rmdir /s /q "%INPUT_DIR%.previous"
if exist "%INPUT_DIR%" move "%INPUT_DIR%" "%INPUT_DIR%.previous" >nul || exit /b 1
move "%EXTRACT_DIR%\core" "%INPUT_DIR%" >nul || exit /b 1

echo Floorp was updated in "%INPUT_DIR%".
if exist "%INPUT_DIR%.previous" echo Previous copy saved as "%INPUT_DIR%.previous".
exit /b 0

:downloadinstaller
if exist "%FLOORP_INSTALLER%" del /q "%FLOORP_INSTALLER%"

call :trydownload "%FLOORP_URL%"
if not errorlevel 1 exit /b 0

echo Current asset name failed. Trying legacy Floorp asset name...
call :trydownload "%FLOORP_LEGACY_URL%"
if not errorlevel 1 exit /b 0

echo Error: failed to download Floorp from:
echo %FLOORP_URL%
echo %FLOORP_LEGACY_URL%
exit /b 1

:trydownload
set "DOWNLOAD_URL=%~1"
if exist "%FLOORP_INSTALLER%" del /q "%FLOORP_INSTALLER%"

where curl.exe >nul 2>&1
if not errorlevel 1 (
    echo Downloading with curl.exe...
    curl.exe -L --fail --retry 3 --retry-delay 2 --connect-timeout 30 -A "FloorpyBuild/1.0" -o "%FLOORP_INSTALLER%" "%DOWNLOAD_URL%"
    if not errorlevel 1 call :validateinstaller && exit /b 0
)

echo Downloading with PowerShell...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -MaximumRedirection 10 -Headers @{'User-Agent'='FloorpyBuild/1.0'} -Uri '%DOWNLOAD_URL%' -OutFile '%FLOORP_INSTALLER%'"
if not errorlevel 1 call :validateinstaller && exit /b 0

exit /b 1

:validateinstaller
if not exist "%FLOORP_INSTALLER%" exit /b 1
for %%I in ("%FLOORP_INSTALLER%") do (
    if %%~zI GTR 1048576 exit /b 0
)
echo Downloaded file is too small to be the Floorp installer.
exit /b 1

:pack
echo.
echo Packing "%INPUT_DIR%"...
call :find7z || exit /b 1
if not exist "%INPUT_DIR%\floorp.exe" (
    echo Error: "%INPUT_DIR%\floorp.exe" was not found.
    exit /b 1
)
if not exist "%RUN_SCRIPT%" (
    echo Error: run.bat was not found.
    exit /b 1
)

if exist "%ARCHIVE%" del /q "%ARCHIVE%"
"%SEVEN_ZIP%" a -t7z -m0=LZMA2 -mx=9 -ms=on "%ARCHIVE%" "%INPUT_DIR%" "%RUN_SCRIPT%"
if errorlevel 1 (
    echo Error: packing failed.
    exit /b 1
)

echo Created "%ARCHIVE%".
exit /b 0

:makesfx
echo.
echo Creating "%OUTPUT_EXE%"...
if not exist "%SFX_MODULE%" (
    echo Error: 7zS264.sfx was not found.
    exit /b 1
)
if not exist "%ARCHIVE%" (
    echo Error: "%ARCHIVE%" was not found. Run the pack step first.
    exit /b 1
)

if exist "%OUTPUT_EXE%" del /q "%OUTPUT_EXE%"
copy /Y /B "%SFX_MODULE%" + "%ARCHIVE%" "%OUTPUT_EXE%" >nul
if errorlevel 1 (
    echo Error: SFX creation failed.
    exit /b 1
)

echo Created "%OUTPUT_EXE%".
exit /b 0

:resourcehack
echo.
echo Updating icon and manifest...
call :findresourcehacker || exit /b 1

if not exist "%OUTPUT_EXE%" (
    echo Error: "%OUTPUT_EXE%" was not found. Run the SFX step first.
    exit /b 1
)
if not exist "%ROOT%icon.ico" (
    echo Error: icon.ico was not found.
    exit /b 1
)
if not exist "%ROOT%Manifest.txt" (
    echo Error: Manifest.txt was not found.
    exit /b 1
)

"%RESOURCE_HACKER%" -open "%OUTPUT_EXE%" -save "%OUTPUT_EXE%" -action addoverwrite -resource "%ROOT%icon.ico" -mask ICONGROUP,MAINICON,0 -log CONSOLE
if errorlevel 1 exit /b 1

"%RESOURCE_HACKER%" -open "%OUTPUT_EXE%" -save "%OUTPUT_EXE%" -action addoverwrite -resource "%ROOT%Manifest.txt" -mask Manifest,1, -log CONSOLE
if errorlevel 1 exit /b 1

echo Resources updated.
exit /b 0

:find7z
set "SEVEN_ZIP="
:: Prefer the CLI builds (7za / 7za64). The 7z.exe GUI binary is intentionally
:: avoided because it spawns a window and is not suitable for scripted use.
if exist "%ROOT_7Z%" set "SEVEN_ZIP=%ROOT_7Z%"
if not defined SEVEN_ZIP if exist "%ProgramFiles%\7-Zip\7za.exe" set "SEVEN_ZIP=%ProgramFiles%\7-Zip\7za.exe"
if not defined SEVEN_ZIP if exist "%ProgramFiles(x86)%\7-Zip\7za.exe" set "SEVEN_ZIP=%ProgramFiles(x86)%\7-Zip\7za.exe"
if not defined SEVEN_ZIP if exist "%ProgramFiles%\7-Zip\7za64.exe" set "SEVEN_ZIP=%ProgramFiles%\7-Zip\7za64.exe"
if not defined SEVEN_ZIP if exist "%ProgramFiles(x86)%\7-Zip\7za64.exe" set "SEVEN_ZIP=%ProgramFiles(x86)%\7-Zip\7za64.exe"
if not defined SEVEN_ZIP for %%I in (7za.exe 7za64.exe) do (
    for /f "delims=" %%P in ('where %%I 2^>nul') do (
        if not defined SEVEN_ZIP set "SEVEN_ZIP=%%P"
    )
)

if not defined SEVEN_ZIP (
    echo Error: 7-Zip command line tool was not found.
    echo Place 7za64.exe next to Build.bat or install 7-Zip CLI.
    exit /b 1
)
exit /b 0

:findresourcehacker
set "RESOURCE_HACKER="
if exist "%ROOT_RH%" set "RESOURCE_HACKER=%ROOT_RH%"
if not defined RESOURCE_HACKER if exist "%ProgramFiles(x86)%\Resource Hacker\ResourceHacker.exe" set "RESOURCE_HACKER=%ProgramFiles(x86)%\Resource Hacker\ResourceHacker.exe"
if not defined RESOURCE_HACKER if exist "%ProgramFiles%\Resource Hacker\ResourceHacker.exe" set "RESOURCE_HACKER=%ProgramFiles%\Resource Hacker\ResourceHacker.exe"

if not defined RESOURCE_HACKER (
    echo Error: ResourceHacker.exe was not found.
    echo Place ResourceHacker.exe next to Build.bat or install Resource Hacker.
    exit /b 1
)
exit /b 0

:ensurepowershell
powershell -NoProfile -Command "exit 0" >nul 2>&1
if errorlevel 1 (
    echo Error: PowerShell was not found.
    exit /b 1
)
exit /b 0

:success
echo.
echo Build completed successfully.
pause
exit /b 0

:failed
echo.
echo Build failed.
pause
exit /b 1

:done
exit /b 0

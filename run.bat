@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ============================================================
:: COMAC AgentOS — run.bat v2.1
:: Auto-detect Python, probe providers, smart menu, repair mode
:: ============================================================

:: ---- Find Python ----
call "%~dp0_find_python.bat"
if errorlevel 1 (
    pause
    exit /b 1
)

call "%~dp0messages\zh.txt"

echo.
echo ============================================================
echo %MSG_TITLE%
echo ============================================================
echo.

:: ---- Step 1: Probe ----
echo %MSG_RUN_PROBING%
"%PYTHON_EXE%" "%~dp0probe.py"
set PROBE_EXIT=%ERRORLEVEL%

:: ---- Step 1b: Self-heal: ensure _runtime.bat exists ----
:: probe.py should have created _runtime.bat. If not (probe crashed before
:: writing, or the user is running an old binary), fall back to the tracked
:: seed: copy _runtime_template.bat (if present) or just create a stub so
:: the `call _runtime.bat 2>nul` below doesn't silently bind empty vars.
if not exist "%~dp0_runtime.bat" (
    if exist "%~dp0_runtime_template.bat" (
        copy /Y "%~dp0_runtime_template.bat" "%~dp0_runtime.bat" >nul
    ) else (
        > "%~dp0_runtime.bat" echo @echo off
        >>"%~dp0_runtime.bat" echo set PROV_COUNT=0
        >>"%~dp0_runtime.bat" echo set PROV_ONLINE_COUNT=0
    )
)

:: ---- Step 2: Handle results ----
if %PROBE_EXIT% equ 3 goto FATAL_CONFIG
if %PROBE_EXIT% equ 0 goto PROBE_OK

:: 0 or partial — check if any providers are online
call "%~dp0_runtime.bat" 2>nul
if "!PROV_ONLINE_COUNT!"=="0" goto REPAIR_MODE
if "!PROV_ONLINE_COUNT!" gtr 0 goto PROBE_OK

:FATAL_CONFIG
echo.
echo ============================================================
echo  CONFIG ERROR — providers.json needs attention
echo ============================================================
echo.
echo  Options:
echo    [1] Open providers.json in Notepad to fix
echo    [2] Run setup.bat to recreate
echo    [Q] Quit
echo.
set /p FIX_CHOICE=Choice (1/2/Q):
if /i "!FIX_CHOICE!"=="1" (start notepad "%~dp0providers.json" & goto RETRY)
if /i "!FIX_CHOICE!"=="2" (call "%~dp0setup.bat" & goto RETRY)
if /i "!FIX_CHOICE!"=="q" exit /b 0
goto FATAL_CONFIG

:REPAIR_MODE
echo.
echo ============================================================
echo  REPAIR MODE — no providers online
echo ============================================================
echo.
echo  Look at the DIAGNOSTICS section above for hints.
echo.
echo  Quick fixes:
echo    [1] Open providers.json to check apiKey / paths
echo    [2] Re-probe (after manual fix)
echo    [3] Start local Qwen (if configured)
echo    [4] Run full verify.bat
echo    [5] Continue anyway (may fail)
echo    [Q] Quit
echo.
set /p REPAIR_CHOICE=Choice (1-5/Q):
if /i "!REPAIR_CHOICE!"=="1" (start notepad "%~dp0providers.json" & pause & goto RETRY)
if /i "!REPAIR_CHOICE!"=="2" goto RETRY
if /i "!REPAIR_CHOICE!"=="3" (call "%~dp0start-qwen.bat" & goto RETRY)
if /i "!REPAIR_CHOICE!"=="4" (call "%~dp0verify.bat" & exit /b !ERRORLEVEL!)
if /i "!REPAIR_CHOICE!"=="5" goto PROBE_OK
if /i "!REPAIR_CHOICE!"=="q" exit /b 0
goto REPAIR_MODE

:RETRY
echo.
echo Re-running probe...
"%PYTHON_EXE%" "%~dp0probe.py"
call "%~dp0_runtime.bat" 2>nul
if "!PROV_ONLINE_COUNT!"=="0" goto REPAIR_MODE

:PROBE_OK
:: ---- Generate context ----
"%PYTHON_EXE%" "%~dp0_generate_context.py" 1>nul 2>nul

:: ---- Source runtime ----
call "%~dp0_runtime.bat" 2>nul

:: ---- Start watchdog (only if not already running) ----
tasklist /fi "WINDOWTITLE eq COMAC-Watchdog" 2>nul | find "cmd.exe" 1>nul 2>nul
if errorlevel 1 (
    start "COMAC-Watchdog" /MIN %ComSpec% /c "%~dp0watchdog.bat"
)

:: ---- Build menu ----
echo.
echo %MSG_RUN_MENU_TITLE%
echo    %MSG_SEPARATOR%

set IDX=1

if "!PROV_NEWAPI_ONLINE!"=="1" (
    echo    [!IDX!] GLM — !PROV_NEWAPI_DISPLAY!
    set MENU_!IDX!_PROV=newapi
    set /a IDX+=1
)

if "!PROV_LLAMACPP_ONLINE!"=="1" (
    echo    [!IDX!] Qwen — !PROV_LLAMACPP_DISPLAY!
    set MENU_!IDX!_PROV=llamacpp
    set /a IDX+=1
)

echo    [V] Verify
echo    [Q] Quit
echo    %MSG_SEPARATOR%

set /p CHOICE=%MSG_RUN_PROMPT%

if /i "!CHOICE!"=="q" exit /b 0
if /i "!CHOICE!"=="v" goto RUN_VERIFY
if "!CHOICE!"=="1" set PROV=!MENU_1_PROV!
if "!CHOICE!"=="2" set PROV=!MENU_2_PROV!
if "!PROV!"=="" (echo Invalid choice & pause & exit /b 1)

goto LAUNCH

:RUN_VERIFY
call "%~dp0verify.bat"
exit /b !ERRORLEVEL!

:LAUNCH
if not exist "%~dp0bin\opencode.exe" (
    echo [FATAL] opencode.exe not found — run setup.bat first
    pause
    exit /b 1
)

if "!PROV!"=="newapi" (
    set MODEL_STR=%PROV_NEWAPI_ID%/%PROV_NEWAPI_MODEL%
    echo %MSG_RUN_STARTING% !PROV_NEWAPI_DISPLAY!
)
if "!PROV!"=="llamacpp" (
    set MODEL_STR=%PROV_LLAMACPP_ID%:%PROV_LLAMACPP_MODEL%
    echo %MSG_RUN_STARTING% !PROV_LLAMACPP_DISPLAY!
)

set OPENCODE_CONFIG=%~dp0opencode.json
"%~dp0bin\opencode.exe" run --model "!MODEL_STR!"

exit /b !ERRORLEVEL!

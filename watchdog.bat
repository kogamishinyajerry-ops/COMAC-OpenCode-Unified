@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: Iron rule #4: prevent duplicate watchdog instances via tasklist dedup
tasklist /fi "WINDOWTITLE eq COMAC-Watchdog" 2>nul | find /i "cmd.exe" >nul
if not errorlevel 1 (
    echo Watchdog already running. Exiting.
    exit /b 0
)
title COMAC-Watchdog

call "%~dp0_find_python.bat"
if errorlevel 1 exit /b 1
call "%~dp0messages\zh.txt"

set INTERVAL=30
set ALERT_LOG=%~dp0agent-memory\alerts.log

:: Iron rule #6: use Python datetime for locale-independent timestamp
for /f "delims=" %%T in ('"%PYTHON_EXE%" -c "import datetime;print(datetime.datetime.now().strftime('%%Y-%%m-%%d %%H:%%M:%%S'))" 2^>nul') do set TS=%%T
echo [!TS!] Watchdog started
if not exist "%ALERT_LOG%" echo COMAC AgentOS Watchdog — session start > "%ALERT_LOG%"

:LOOP
timeout /t %INTERVAL% /nobreak >nul

"%PYTHON_EXE%" "%~dp0probe.py" 1>nul 2>nul
call "%~dp0_runtime.bat" 2>nul

:: Per-tick timestamp via Python (locale-safe, no %date%/%time% brittleness)
for /f "delims=" %%T in ('"%PYTHON_EXE%" -c "import datetime;print(datetime.datetime.now().strftime('%%Y-%%m-%%d %%H:%%M:%%S'))" 2^>nul') do set TS=%%T
if "!PROV_ONLINE_COUNT!"=="0" (
    echo [!TS!] ALERT: all providers down >> "%ALERT_LOG%"
) else (
    echo [!TS!] OK: !PROV_ONLINE_COUNT! online >> "%ALERT_LOG%"
)

goto LOOP

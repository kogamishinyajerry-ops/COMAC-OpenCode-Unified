@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

call "%~dp0messages\zh.txt"

:: Default port, override from runtime if available
set QWEN_PORT=11435
if exist "%~dp0_runtime.bat" call "%~dp0_runtime.bat" 2>nul
if defined PROV_LLAMACPP_PORT set QWEN_PORT=!PROV_LLAMACPP_PORT!

:: Use netstat to find PID on given port (locale-safe: grep for port number)
set PID=
for /f "tokens=1,2,5" %%a in ('netstat -ano 2^>nul ^| findstr /r ":%QWEN_PORT% "') do (
    echo %%b | findstr /r "^[0-9]" 1>nul 2>nul
    if not errorlevel 1 (
        set PID=%%c
        goto KILL_IT
    )
)

echo [INFO] No process on port %QWEN_PORT%
goto DONE

:KILL_IT
echo %MSG_QWEN_STOPPING%
taskkill /PID !PID! /F 1>nul 2>nul
if errorlevel 1 (
    echo [WARN] Failed to stop PID !PID!
) else (
    echo %MSG_QWEN_STOPPED%
)

:DONE
exit /b 0

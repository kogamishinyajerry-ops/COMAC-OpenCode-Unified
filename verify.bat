@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

call "%~dp0_find_python.bat"
if errorlevel 1 exit /b 1
call "%~dp0messages\zh.txt"

echo.
echo ============================================================
echo %MSG_VERIFY_TITLE%
echo ============================================================
echo.

echo %MSG_VERIFY_PROBE%
"%PYTHON_EXE%" "%~dp0probe.py"
set ONLINE=%ERRORLEVEL%
echo.

echo %MSG_VERIFY_CONTEXT%
"%PYTHON_EXE%" "%~dp0_generate_context.py"
echo.

echo %MSG_VERIFY_BINARY%
if exist "%~dp0bin\opencode.exe" (
    echo    %MSG_OK% opencode.exe found
) else (
    echo    %MSG_FAIL% opencode.exe missing — run setup.bat
)
echo.

echo %MSG_VERIFY_CONFIG%
if exist "%~dp0providers.json" (
    echo    %MSG_OK% providers.json found
) else (
    echo    %MSG_FAIL% providers.json missing
)
if exist "%~dp0opencode.json" (
    echo    %MSG_OK% opencode.json (auto-generated)
) else (
    echo    %MSG_WARN% opencode.json not found
)
echo.

echo ============================================================
call "%~dp0_runtime.bat" 2>nul
if "!PROV_ONLINE_COUNT!" gtr 0 (
    echo %MSG_VERIFY_ALL_OK% (!PROV_ONLINE_COUNT! provider(s) online)
    echo ============================================================
    exit /b 0
)
:: No providers online — distinguish between config issue and network issue
if exist "%~dp0providers.json" (
    echo %MSG_VERIFY_NO_PROVIDER%
) else (
    echo %MSG_VERIFY_HAS_FAIL%
)
echo ============================================================
echo.
pause
exit /b 1

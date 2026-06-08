@echo off
chcp 65001 >nul 2>&1

call "%~dp0_find_python.bat"
if errorlevel 1 exit /b 1
call "%~dp0messages\zh.txt"

echo ============================================================
echo %MSG_TITLE%
echo ============================================================
echo.

echo %MSG_QWEN_STARTING%
"%PYTHON_EXE%" "%~dp0probe.py"

echo.
echo Done. Check status above for Qwen provider.
exit /b 0

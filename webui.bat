@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%_find_python.bat"
if errorlevel 1 ( pause & exit /b 1 )
echo COMAC AgentOS - WebUI starting on http://127.0.0.1:8080
echo Press Ctrl+C in this window to stop.
echo.
"%PYTHON_EXE%" "%SCRIPT_DIR%webui.py"
exit /b %ERRORLEVEL%

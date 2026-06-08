@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%_find_python.bat"
if errorlevel 1 ( pause & exit /b 1 )
"%PYTHON_EXE%" -u "%SCRIPT_DIR%switch.py"
exit /b %ERRORLEVEL%

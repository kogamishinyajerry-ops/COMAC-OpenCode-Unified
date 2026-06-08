@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
set "SCRIPT_DIR=%~dp0"

:: ============================================================
:: COMAC AgentOS - aliases installer
:: Drops 6 .bat wrappers into %USERPROFILE%\bin\ so you can
:: invoke comac, comac-doctor, comac-webui, comac-switch,
:: comac-bench, comac-archive from any directory.
::
:: Uninstall:  comac-uninstall  (created by this script)
:: ============================================================

set "BIN_DIR=%USERPROFILE%\bin"
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

echo.
echo ============================================================
echo  COMAC AgentOS - Installing command aliases
echo ============================================================
echo  Target: %BIN_DIR%
echo.

set RC=0

:: --- comac (root launcher) ---
(
    echo @echo off
    echo call "%SCRIPT_DIR%run.bat" %%*
) > "%BIN_DIR%\comac.bat"
if errorlevel 1 (echo [FAIL] comac.bat & set RC=1) else (echo [OK]   comac.bat)

:: --- comac-doctor ---
(
    echo @echo off
    echo call "%SCRIPT_DIR%doctor.bat" %%*
) > "%BIN_DIR%\comac-doctor.bat"
if errorlevel 1 (echo [FAIL] comac-doctor.bat & set RC=1) else (echo [OK]   comac-doctor.bat)

:: --- comac-webui ---
(
    echo @echo off
    echo call "%SCRIPT_DIR%webui.bat" %%*
) > "%BIN_DIR%\comac-webui.bat"
if errorlevel 1 (echo [FAIL] comac-webui.bat & set RC=1) else (echo [OK]   comac-webui.bat)

:: --- comac-switch ---
(
    echo @echo off
    echo call "%SCRIPT_DIR%switch.bat" %%*
) > "%BIN_DIR%\comac-switch.bat"
if errorlevel 1 (echo [FAIL] comac-switch.bat & set RC=1) else (echo [OK]   comac-switch.bat)

:: --- comac-bench ---
(
    echo @echo off
    echo call "%SCRIPT_DIR%benchmark.bat" %%*
) > "%BIN_DIR%\comac-bench.bat"
if errorlevel 1 (echo [FAIL] comac-bench.bat & set RC=1) else (echo [OK]   comac-bench.bat)

:: --- comac-archive ---
(
    echo @echo off
    echo call "%SCRIPT_DIR%archive.bat" %%*
) > "%BIN_DIR%\comac-archive.bat"
if errorlevel 1 (echo [FAIL] comac-archive.bat & set RC=1) else (echo [OK]   comac-archive.bat)

:: --- comac-uninstall ---
(
    echo @echo off
    echo del /Q "%BIN_DIR%\comac.bat" 2^>nul
    echo del /Q "%BIN_DIR%\comac-doctor.bat" 2^>nul
    echo del /Q "%BIN_DIR%\comac-webui.bat" 2^>nul
    echo del /Q "%BIN_DIR%\comac-switch.bat" 2^>nul
    echo del /Q "%BIN_DIR%\comac-bench.bat" 2^>nul
    echo del /Q "%BIN_DIR%\comac-archive.bat" 2^>nul
    echo del /Q "%BIN_DIR%\comac-uninstall.bat" 2^>nul
    echo echo COMAC aliases removed.
) > "%BIN_DIR%\comac-uninstall.bat"
if errorlevel 1 (echo [FAIL] comac-uninstall.bat & set RC=1) else (echo [OK]   comac-uninstall.bat)

echo.
echo ============================================================
if %RC%==0 (
    echo  [OK] All 7 aliases installed.
) else (
    echo  [WARN] Some aliases failed to write.
)
echo ============================================================
echo.
echo  Next steps:
echo    1. Add %%USERPROFILE%%\bin to your PATH (one-time):
echo         setx PATH "%%PATH%%%%;%USERPROFILE%%\bin"
echo    2. Open a new CMD window, then test:
echo         comac-doctor
echo.
echo  To uninstall later:  comac-uninstall
echo.
exit /b %RC%

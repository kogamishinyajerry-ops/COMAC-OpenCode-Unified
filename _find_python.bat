@echo off
:: ============================================================
:: _find_python.bat — Auto-detect Python 3.11+
:: Sets PYTHON_EXE. Source from any .bat script.
:: ============================================================

if defined PYTHON_EXE exit /b 0

:: Try PATH first (most reliable across machines)
for /f "delims=" %%p in ('where python.exe 2^>nul') do (
    "%%~p" -c "import sys; sys.exit(0 if sys.version_info.major==3 and sys.version_info.minor>=11 else 1)" 1>nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=%%~p"
        exit /b 0
    )
)

:: Fallback: check common install paths (C:, D:, E: drives)
set "_found="
for %%d in (C D E) do (
    if exist "%%d:\Python\python.exe" (
        "%%d:\Python\python.exe" -c "import sys; sys.exit(0 if sys.version_info.major==3 and sys.version_info.minor>=11 else 1)" 1>nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_EXE=%%d:\Python\python.exe"
            set "_found=1"
        )
    )
    if not defined _found for /d %%v in ("%%d:\Python3*") do (
        if exist "%%v\python.exe" (
            "%%v\python.exe" -c "import sys; sys.exit(0 if sys.version_info.major==3 and sys.version_info.minor>=11 else 1)" 1>nul 2>nul
            if not errorlevel 1 (
                set "PYTHON_EXE=%%v\python.exe"
                set "_found=1"
            )
        )
    )
)

if defined _found exit /b 0

:: Try LOCALAPPDATA
if defined LOCALAPPDATA (
    for /d %%v in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
        if exist "%%v\python.exe" (
            "%%v\python.exe" -c "import sys; sys.exit(0 if sys.version_info.major==3 and sys.version_info.minor>=11 else 1)" 1>nul 2>nul
            if not errorlevel 1 (
                set "PYTHON_EXE=%%v\python.exe"
                set "_found=1"
            )
        )
    )
)

if defined _found exit /b 0

:: Final attempt: py launcher
for /f "delims=" %%p in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
    if not "%%p"=="" (
        "%%~p" -c "import sys; sys.exit(0 if sys.version_info.major==3 and sys.version_info.minor>=11 else 1)" 1>nul 2>nul
        if not errorlevel 1 (
            set "PYTHON_EXE=%%~p"
            exit /b 0
        )
    )
)

:: Not found
echo [FATAL] Python 3.11+ not found
echo.
echo Install Python 3.11+ from python.org
echo Enable "Add Python to PATH" during install
echo.
echo Or set manually:
echo   set PYTHON_EXE=C:\path\to\python.exe
echo   then re-run this script
exit /b 1

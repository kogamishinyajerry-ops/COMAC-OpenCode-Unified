@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: ============================================================
:: COMAC AgentOS — setup.bat v2.1
:: First-time deployment: extract + configure + probe + memory
:: ============================================================

call "%~dp0_find_python.bat"
if errorlevel 1 pause && exit /b 1
call "%~dp0messages\zh.txt"
set FAIL=0

echo.
echo ============================================================
echo %MSG_SETUP_TITLE%
echo ============================================================
echo.

:: ---- Step 1: Extract OpenCode ----
echo %MSG_SETUP_STEP1%
if exist "%~dp0bin\opencode.exe" (
    echo    %MSG_OK% OpenCode already installed
    goto STEP2
)

if not exist "%~dp0downloads\opencode-windows-x64.zip" (
    echo    %MSG_FAIL% opencode-windows-x64.zip not found
    echo    Place it in downloads\ and re-run
    set /a FAIL+=1
    goto STEP2
)

:: Extract via Python zipfile (stdlib) — replaces PowerShell Expand-Archive
:: Iron rule #10: completely abandoned PowerShell, use CMD + Python only
echo    Extracting via Python zipfile...
"%PYTHON_EXE%" -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "%~dp0downloads\opencode-windows-x64.zip" "%~dp0bin\"
if errorlevel 1 (
    echo    %MSG_FAIL% Extraction failed — check zip integrity
    set /a FAIL+=1
    goto STEP2
)
if exist "%~dp0bin\opencode.exe" (
    echo    %MSG_OK% OpenCode extracted
) else (
    echo    %MSG_FAIL% Extraction succeeded but opencode.exe missing
    set /a FAIL+=1
)

:: ---- Step 2: Configure providers.json ----
:STEP2
echo %MSG_SETUP_STEP2%
if not exist "%~dp0providers.json" (
    echo    %MSG_FAIL% providers.json missing
    set /a FAIL+=1
    goto STEP4
)
echo    %MSG_OK% providers.json found
echo.
echo    ============================================
echo    CONFIGURATION REQUIRED
echo    ============================================
echo    Edit providers.json and set:
echo      [newapi]  apiKey = your real New API key
echo      [llamacpp] modelPath = path to Qwen GGUF
echo    ============================================
echo.
echo    Opening providers.json...
start notepad "%~dp0providers.json"
echo.
echo    Press any key AFTER you saved providers.json...
pause >nul

:: ---- Step 3: Probe ----
:STEP3
echo %MSG_SETUP_STEP3%
"%PYTHON_EXE%" "%~dp0probe.py"

:: ---- Step 4: Init memory ----
:STEP4
echo %MSG_SETUP_STEP4%
if not exist "%~dp0agent-memory" mkdir "%~dp0agent-memory"
if not exist "%~dp0agent-memory\sessions" mkdir "%~dp0agent-memory\sessions"
"%PYTHON_EXE%" "%~dp0_generate_context.py" 2>nul
echo    %MSG_OK% Memory system ready

echo.
echo ============================================================
echo %MSG_SETUP_DONE%
echo ============================================================
echo %MSG_SETUP_NEXT%
echo.

if !FAIL! gtr 0 exit /b 1
exit /b 0

@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

call "%~dp0_find_python.bat"
if errorlevel 1 exit /b 1

set MEMORY_DIR=%~dp0agent-memory
set FACTS_FILE=%MEMORY_DIR%\FACTS.json
set CONTEXT_FILE=%MEMORY_DIR%\CONTEXT.md

set CMD=%1
set ARG1=%2
set ARG2=%3

if "%CMD%"=="" goto HELP
if /i "%CMD%"=="add" goto ADD_FACT
if /i "%CMD%"=="recall" goto RECALL_FACT
if /i "%CMD%"=="list" goto LIST_FACTS
if /i "%CMD%"=="context" goto SHOW_CONTEXT
if /i "%CMD%"=="log" goto LOG_SESSION
if /i "%CMD%"=="probe" goto RUN_PROBE
if /i "%CMD%"=="help" goto HELP
echo Unknown command: %CMD%
goto HELP

:HELP
echo.
echo COMAC AgentOS — Memory CLI
echo ============================================================
echo   memory add   "key" "value"    Store a fact
echo   memory recall "key"           Retrieve a fact
echo   memory list                   List all facts
echo   memory context                Show current context
echo   memory log   "message"        Append to session log
echo   memory probe                  Re-run provider detection
echo ============================================================
goto DONE

:ADD_FACT
if "%ARG1%"=="" (echo Usage: memory add "key" "value" & goto DONE)
if "%ARG2%"=="" (echo Usage: memory add "key" "value" & goto DONE)
"%PYTHON_EXE%" -c "import json;d=json.load(open('%FACTS_FILE%','r',encoding='utf-8'));d['facts']['%ARG1%']='%ARG2%';json.dump(d,open('%FACTS_FILE%','w',encoding='utf-8'),indent=2,ensure_ascii=False)" 2>nul
if errorlevel 1 (echo [FAIL] Could not add fact) else (echo [OK] Stored: %ARG1% = %ARG2%)
goto DONE

:RECALL_FACT
if "%ARG1%"=="" (echo Usage: memory recall "key" & goto DONE)
"%PYTHON_EXE%" -c "import json;d=json.load(open('%FACTS_FILE%','r',encoding='utf-8'));print(d['facts'].get('%ARG1%','(not found)'))" 2>nul
goto DONE

:LIST_FACTS
echo === Stored Facts ===
"%PYTHON_EXE%" -c "import json;d=json.load(open('%FACTS_FILE%','r',encoding='utf-8'));[print(f'  {k}: {v}') for k,v in d.get('facts',{}).items()]" 2>nul
echo ===================
goto DONE

:SHOW_CONTEXT
if exist "%CONTEXT_FILE%" (type "%CONTEXT_FILE%") else (echo CONTEXT.md not found)
goto DONE

:LOG_SESSION
if "%ARG1%"=="" (echo Usage: memory log "message" & goto DONE)
:: Iron rule #6: locale-independent timestamp via Python
for /f "delims=" %%d in ('"%PYTHON_EXE%" -c "import datetime;print(datetime.date.today())" 2^>nul') do set TODAY=%%d
for /f "delims=" %%T in ('"%PYTHON_EXE%" -c "import datetime;print(datetime.datetime.now().strftime('%%Y-%%m-%%d %%H:%%M:%%S'))" 2^>nul') do set TS=%%T
set LOG_FILE=%MEMORY_DIR%\sessions\%TODAY%.md
echo [!TS!] %ARG1% %ARG2% %3 %4 %5 %6 %7 %8 %9 >> "%LOG_FILE%"
echo [OK] Logged to %TODAY%.md
goto DONE

:RUN_PROBE
"%PYTHON_EXE%" "%~dp0probe.py"
"%PYTHON_EXE%" "%~dp0_generate_context.py"
goto DONE

:DONE
exit /b 0

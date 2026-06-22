@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if not exist "%~dp0.env" (
    echo [ERROR] .env file was not found in:
    echo %~dp0
    pause
    exit /b 1
)

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" "%~dp0kis_live_once_stdlib.py"
    goto finished
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0kis_live_once_stdlib.py"
    goto finished
)

where python >nul 2>nul
if not errorlevel 1 (
    python "%~dp0kis_live_once_stdlib.py"
    goto finished
)

echo [ERROR] Python 3 was not found.
echo Install Python 3 and try again.
pause
exit /b 1

:finished
echo.
echo Exit code: %ERRORLEVEL%
pause

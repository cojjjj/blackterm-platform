@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [BLACKTERM] Creating virtual environment...
    py -m venv .venv
    if errorlevel 1 goto :error
)

echo [BLACKTERM] Activating environment...
call ".venv\Scripts\activate.bat"

echo [BLACKTERM] Installing or updating dependencies...
python -m pip install -e .
if errorlevel 1 goto :error

echo [BLACKTERM] Launching Intelligence Platform...
python -m blackterm_recon.desktop.app
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo BLACKTERM could not start. Review the error above.
pause
exit /b 1

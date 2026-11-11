@echo off
chcp 65001 >nul
set "PY_CMD=python"
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
)
echo ========================================================================================
echo   EGITIMI SIFIRLA VE 1. BOLUMDEN BASTAN BASLAT
echo ========================================================================================
set "RUN_DIR=%~dp0artifacts\v2\cologne3-fresh-%RANDOM%-%RANDOM%"
echo Yeni egitim dizini: %RUN_DIR%
"%PY_CMD%" -u "%~dp0src\corridor3_runner.py" train --output-dir "%RUN_DIR%"
echo.
pause

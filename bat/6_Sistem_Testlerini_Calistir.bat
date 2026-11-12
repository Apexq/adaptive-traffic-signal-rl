@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "PY_CMD=python"
if exist "%~dp0..\.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0..\.venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
)
echo =================================================================================
echo   KOD TABANI VE SIMULASYON DOGRULAMA TESTLERI (20 REGRESYON TESTI)
echo =================================================================================
set "RUN_SUMO_TESTS=1"
"%PY_CMD%" -m unittest discover -s tests -v
echo.
pause

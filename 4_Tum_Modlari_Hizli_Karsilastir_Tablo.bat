@echo off
chcp 65001 >nul
set "PY_CMD=python"
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
)
echo =================================================================================
echo   3 ARDISIK KAVSAKLI KORIDOR (COLOGNE-3) - HIZLI KARSILASTIRMA TESTI
echo =================================================================================
echo Simdi arka planda sirasiyla:
echo   1) Fixed-Time (Sabit Sureli)
echo   2) Actuated (Klasik Sensorlu)
echo   3) DQN RL (Akilli Adaptif - Onerilen)
echo 1800 saniye boyunca 3 kavsakli koridorda calistirilip sonuclar karsilastiriliyor...
echo.
"%PY_CMD%" "%~dp0src\corridor3_runner.py" compare
echo.
pause

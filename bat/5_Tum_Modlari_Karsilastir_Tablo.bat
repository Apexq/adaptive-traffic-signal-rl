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
echo   4 MOD KARSILASTIRMA BENCHMARK TESTI (Fixed vs Actuated vs MaxPressure vs DQN)
echo =================================================================================
echo Simdi arka planda sirasiyla:
echo   1) Fixed-Time (Sabit Sureli)
echo   2) Actuated (Klasik Sensorlu)
echo   3) Max-Pressure (Basinc Tabanli Adaptif)
echo   4) DQN RL (Akilli Derin Pekistirmeli Ogrenme)
echo Cologne-3 koridorunda test edilip karsilastirmali metrik tablosu cikarilacaktir...
echo.
"%PY_CMD%" src\corridor3_runner.py compare --duration 1800
echo.
pause

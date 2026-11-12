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
echo   4. MOD: AKILLI PEKISTIRMELI OGRENME (DQN RL) - COLOGNE-3 KORIDORU
echo =================================================================================
echo Derin Q-Ogrenme (DQN) Yapay Zeka modeli: 3 kavsagin tum faz vektorlerini ve
echo zaman saatlerini analiz ederek kuyrugu ve gecikmeyi en cok azaltacak faza gecer.
echo.
echo [IZLEME ADIMLARI]
echo   1. Acilan SUMO-GUI penceresinde sol ustteki YESIL PLAY butonuna basin.
echo   2. Yandaki konsol penceresinden yapay zekanin canli faz kararlarini izleyin.
echo =================================================================================
"%PY_CMD%" src\corridor3_runner.py dqn
pause

@echo off
chcp 65001 >nul
set "PY_CMD=python"
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
)
echo ============================================================================
echo   SUMO-RL ADAPTIVE TRAFFIC CONTROL - LIVE GUI DEMONSTRATION (DQN AGENT)
echo ============================================================================
"%PY_CMD%" "%~dp0src\demo_gui.py" dqn

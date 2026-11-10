@echo off
chcp 65001 >nul
echo ============================================================================
echo   SUMO-RL ADAPTIVE TRAFFIC CONTROL - LIVE GUI DEMONSTRATION (DQN AGENT)
echo ============================================================================
"C:\Users\besir_secilmis\AppData\Local\Python\bin\python.exe" "%~dp0src\demo_gui.py" dqn

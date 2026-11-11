@echo off
chcp 65001 >nul
set "PY_CMD=python"
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Python\bin\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Python\bin\python.exe"
)
echo ========================================================================================
echo   50 BOLUMLUK GERCEK KOLN (COLOGNE-3) 4 FAZLI AKILLI DQN EGITIMI (CHECKPOINT DESTEKLI)
echo ========================================================================================
echo   - Bu pencereyi istediginiz zaman kapatabilir veya Ctrl+C ile durdurabilirsiniz.
echo   - Tekrar actiginizda kaldigi bolumden (episode) otomatik devam edecektir!
echo   - Tamamen cevrimdisi (internetsiz) calisir.
echo ========================================================================================
echo.
"%PY_CMD%" -u "%~dp0src\corridor3_runner.py" train
echo.
pause

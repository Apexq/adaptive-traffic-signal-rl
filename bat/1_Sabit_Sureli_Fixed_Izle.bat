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
echo   1. MOD: SABIT SURELI (FIXED-TIME) KLASIK KONTROL - COLOGNE-3 KORIDORU
echo =================================================================================
echo Klasik sabit zamanli trafik isiklari: Trafik durumuna bakmaksizin sabit dongude
echo fazlari sirasiyla cevirir.
echo.
echo [IZLEME ADIMLARI]
echo   1. Acilan SUMO-GUI penceresinde sol ustteki YESIL PLAY butonuna basin.
echo   2. Yandaki konsol penceresinden kuyruk durumunu takip edin.
echo =================================================================================
"%PY_CMD%" src\corridor3_runner.py fixed
pause

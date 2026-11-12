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
echo   3. MOD: MAX-PRESSURE ADAPTIF KONTROL - COLOGNE-3 KORIDORU
echo =================================================================================
echo Varaiya (2013) Max-Pressure mantigi: Giris kuyrugu ve yaklasan arac yogunlugu ile
echo cikis yogunlugu farkini hesaplayarak maksimum net basınca sahip faza oncelik verir.
echo.
echo [IZLEME ADIMLARI]
echo   1. Acilan SUMO-GUI penceresinde sol ustteki YESIL PLAY butonuna basin.
echo   2. Yandaki konsol penceresinden anlik kararlari izleyin.
echo =================================================================================
"%PY_CMD%" src\corridor3_runner.py maxpressure
pause

@echo off
title TrafficRL Web Vitrini
cd /d "%~dp0.."

echo ========================================================
echo   TrafficRL Akademik Vitrin & Simulasyon Oynaticisi
echo ========================================================
echo.
echo Yerel web sunucusu baslatiliyor: http://localhost:8080
echo Kapatmak icin bu pencereyi kapatin veya CTRL+C basin.
echo.

start "" "http://localhost:8080"

where python >nul 2>nul
if %errorlevel%==0 (
    python -m http.server 8080 --directory web
    goto :eof
)

py -m http.server 8080 --directory web

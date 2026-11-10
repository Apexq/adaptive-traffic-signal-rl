@echo off
chcp 65001 >nul
echo ========================================================================================
echo   EGITIMI SIFIRLA VE 1. BOLUMDEN BASTAN BASLAT
echo ========================================================================================
"C:\Users\besir_secilmis\AppData\Local\Python\bin\python.exe" -u "%~dp0src\corridor3_runner.py" train --reset
echo.
pause

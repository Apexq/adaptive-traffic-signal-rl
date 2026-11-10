@echo off
chcp 65001 >nul
echo =================================================================================
echo   2. DURUM: SENSORLU (ACTUATED / GAP-OUT) TRAFIK ISIGI - 3 KAVSAKLI KORIDOR
echo =================================================================================
echo Bu modda 3 kavsaktaki isiklar (TL_1, TL_2, TL_3) yesil yanan seritte arac
echo kalmadiginda (<=2 arac) yesili erken kesip bekleyen yone aktarir.
echo.
echo [NASIL IZLENIR?]
echo   1. Acilan SUMO-GUI penceresinde sol ustteki YESIL PLAY (Calistir) tusuna basin.
echo   2. Yandaki bu siyah ekranda her 10 saniyede bir 3 kavsagin kuyruk sayilari yazacaktir.
echo =================================================================================
"C:\Users\besir_secilmis\AppData\Local\Python\bin\python.exe" "%~dp0src\corridor3_runner.py" actuated
pause

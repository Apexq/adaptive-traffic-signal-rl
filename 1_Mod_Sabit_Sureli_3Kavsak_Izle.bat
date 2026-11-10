@echo off
chcp 65001 >nul
echo =================================================================================
echo   1. DURUM: SABIT SURELI (FIXED-TIME) KLASIK TRAFIK ISIGI - 3 KAVSAKLI KORIDOR
echo =================================================================================
echo Bu modda 3 kavsaktaki isiklar (TL_1, TL_2, TL_3) yogunluga hic bakmadan
echo sabit 40 saniyede bir degisir.
echo.
echo [NASIL IZLENIR?]
echo   1. Acilan SUMO-GUI penceresinde sol ustteki YESIL PLAY (Calistir) tusuna basin.
echo   2. Yandaki bu siyah ekranda her 10 saniyede bir 3 kavsagin kuyruk sayilari yazacaktir.
echo   3. Ozellikle 0-600 sn arasinda Dogu-Bati bulvarinda ve 600. saniyeden sonra
echo      Kuzey-Guney yan caddelerde kuyruklarin nasil sistigine dikkat edin!
echo =================================================================================
"C:\Users\besir_secilmis\AppData\Local\Python\bin\python.exe" "%~dp0src\corridor3_runner.py" fixed
pause

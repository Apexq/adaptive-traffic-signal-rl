@echo off
chcp 65001 >nul
echo =================================================================================
echo   3. DURUM: AKILLI DERIN PEKISTIRMELI OGRENME (DQN RL) - 3 KAVSAKLI KORIDOR
echo =================================================================================
echo Bu modda egitilmis DQN Yapay Zeka ajani her 5 saniyede bir 3 kavsagin (TL_1, TL_2, TL_3)
echo kuyruk, yaklasan arac yogunlugu ve bekleme suresi vektorunu okuyarak en uygun
echo yesil isik fazini dinamik secer.
echo.
echo [NASIL IZLENIR?]
echo   1. Acilan SUMO-GUI penceresinde sol ustteki YESIL PLAY (Calistir) tusuna basin.
echo   2. Yandaki bu siyah ekranda her 10 saniyede bir 3 kavsagin canli kararlarini izleyin!
echo =================================================================================
"C:\Users\besir_secilmis\AppData\Local\Python\bin\python.exe" "%~dp0src\corridor3_runner.py" dqn
pause

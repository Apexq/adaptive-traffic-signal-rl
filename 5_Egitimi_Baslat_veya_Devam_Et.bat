@echo off
chcp 65001 >nul
echo ========================================================================================
echo   50 BOLUMLUK GERCEK KOLN (COLOGNE-3) 4 FAZLI AKILLI DQN EGITIMI (CHECKPOINT DESTEKLI)
echo ========================================================================================
echo   - Bu pencereyi istediginiz zaman kapatabilir veya Ctrl+C ile durdurabilirsiniz.
echo   - Tekrar actiginizda kaldigi bolumden (episode) otomatik devam edecektir!
echo   - Tamamen cevrimdisi (internetsiz) calisir.
echo ========================================================================================
echo.
"C:\Users\besir_secilmis\AppData\Local\Python\bin\python.exe" -u "%~dp0src\corridor3_runner.py" train
echo.
pause

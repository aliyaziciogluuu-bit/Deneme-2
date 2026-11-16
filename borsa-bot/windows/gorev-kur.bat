@echo off
rem BIST Bot - Windows Gorev Zamanlayici'ya hafta ici her sabah 09:25 icin gorev ekler.
rem Bilgisayar o saatte acik, oturum acilmis ve Matriks IQ calisiyor olmalidir.
schtasks /Create /TN "BIST Bot Emir" /TR "\"%~dp0emir.bat\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 09:25 /F
echo.
echo Gorev eklendi. Kaldirmak icin:  schtasks /Delete /TN "BIST Bot Emir" /F
pause

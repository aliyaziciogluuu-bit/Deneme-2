@echo off
rem BIST Bot - Windows kurulumu (bir kez calistirin). Python 3.11+ kurulu olmalidir.
cd /d "%~dp0.."
python -m venv .venv || goto :hata
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt || goto :hata
if not exist emir-ayar.toml copy emir-ayar.ornek.toml emir-ayar.toml
echo.
echo Kurulum tamam. emir-ayar.toml dosyasini duzenleyin, sonra windows\emir.bat ile deneyin.
pause
exit /b 0
:hata
echo Kurulum basarisiz. Python 3.11 veya ustu kurulu mu? (python.org)
pause
exit /b 1

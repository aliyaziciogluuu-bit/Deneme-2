@echo off
rem BIST Bot - gunun emir fisini isler (Telegram onayi bekler). Matriks IQ acik olmalidir.
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python -m bistbot emir %* >> .emir-cikti.log 2>&1

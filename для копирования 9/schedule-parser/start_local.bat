@echo off
chcp 65001 >nul
rem Локальный запуск парсера для разработки: 127.0.0.1:8001
rem с автоперезапуском при правках кода (PARSER_RELOAD=1).
rem Зависимости один раз ставятся батником install.bat.

cd /d "%~dp0"
set PYTHONUTF8=1
set PARSER_HOST=127.0.0.1
set PARSER_RELOAD=1
python main.py
pause

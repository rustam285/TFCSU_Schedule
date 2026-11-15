@echo off
chcp 65001 >nul
rem Запуск парсера расписания (FastAPI/uvicorn, порт 8001).
rem Зависимости ставятся ОДИН РАЗ отдельным батником install.bat.
rem Раньше здесь выполнялся pip install при каждом запуске: на серверном
rem Python 3.15 он падал каждый раз (нет готовых wheel-ов pydantic-core/pyyaml,
rem а компилятора на сервере нет) и заваливал консоль ошибками сборки,
rem хотя рабочие версии библиотек уже были установлены.

cd /d "%~dp0"

rem Юникод-вывод Python: русские буквы в консоли и логе без кракозябр
set PYTHONUTF8=1

if not exist "logs" mkdir logs

echo ===== %date% %time% : старт парсера ===== >>logs\parser.log
python main.py >>logs\parser.log 2>&1
set EXITCODE=%ERRORLEVEL%
echo ===== %date% %time% : парсер остановлен, код ошибки %EXITCODE% ===== >>logs\parser.log
echo.
echo ************************************************************
echo  Парсер остановлен с кодом ошибки %EXITCODE%.
echo  Последние строки logs\parser.log:
echo ************************************************************
powershell -NoProfile -Command "Get-Content -Tail 30 -Encoding UTF8 'logs\parser.log'"
echo.
pause
exit /b %EXITCODE%

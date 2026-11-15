@echo off
chcp 65001 >nul
rem Запуск сайта расписания на сервере (прод-режим, waitress, порт 8100).
rem Подготовка выполняется ОДИН РАЗ (не при каждом запуске!):
rem   1) скопировать server_env.bat.example в server_env.bat и заполнить (см. DEPLOY.md)
rem   2) python -m venv .venv
rem   3) .venv\Scripts\pip install -r requirements.txt
rem   4) .venv\Scripts\python.exe -m django collectstatic --settings=djangoProject.settings --noinput
rem   5) в папке schedule-parser один раз выполнить install.bat

cd /d "%~dp0"

if exist "server_env.bat" goto env_ok
echo ОШИБКА: нет файла server_env.bat с настройками (DJANGO_SECRET_KEY и др.).
echo Скопируй server_env.bat.example в server_env.bat и заполни его. Подробности в DEPLOY.md.
pause
exit /b 1

:env_ok
rem Секреты берём из локального server_env.bat: файл не хранится в git,
rem и его видит процесс, запущенный планировщиком от SYSTEM
rem (переменные, заданные через setx, процессу от SYSTEM НЕ видны -
rem из-за этого сайт раньше стартовал с чужим ключом: "Session data corrupted").
call "server_env.bat"

rem Юникод-вывод Python: русские буквы в консоли и логе без кракозябр
set PYTHONUTF8=1

if not exist "logs" mkdir logs

rem Парсер расписания - в отдельном окне, его лог: schedule-parser\logs\parser.log
start "" /D "schedule-parser" "start.bat"

echo Сайт запускается... Весь вывод пишется в logs\site.log, это окно можно свернуть.

if exist ".venv\Scripts\waitress-serve.exe" goto run_site
echo waitress не установлен. Выполни один раз: .venv\Scripts\pip install -r requirements.txt
pause
exit /b 1

:run_site
echo ===== %date% %time% : старт сайта ===== >>logs\site.log
".venv\Scripts\waitress-serve.exe" --host=0.0.0.0 --port=8100 djangoProject.wsgi:application >>logs\site.log 2>&1
set EXITCODE=%ERRORLEVEL%
echo ===== %date% %time% : сайт остановлен, код ошибки %EXITCODE% ===== >>logs\site.log
echo.
echo ************************************************************
echo  Сайт остановлен с кодом ошибки %EXITCODE%.
echo  Последние строки logs\site.log:
echo ************************************************************
powershell -NoProfile -Command "Get-Content -Tail 30 -Encoding UTF8 'logs\site.log'"
echo.
pause
exit /b %EXITCODE%

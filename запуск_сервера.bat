@echo off
chcp 65001
rem Запуск сайта расписания на сервере (прод-режим, waitress, порт 8100).
rem Перед первым запуском на сервере один раз выполнить:
rem   1) .venv\Scripts\pip install -r requirements.txt
rem   2) .venv\Scripts\python.exe -m django collectstatic --settings=djangoProject.settings --noinput
rem   3) задать переменные окружения DJANGO_SECRET_KEY / DJANGO_DEBUG / DJANGO_ALLOWED_HOSTS (см. DEPLOY.md)

cd /d "%~dp0"

.venv\Scripts\pip install -r requirements.txt

if exist ".venv\Scripts\waitress-serve.exe" (
    ".venv\Scripts\waitress-serve.exe" --host=0.0.0.0 --port=8100 djangoProject.wsgi:application
) else (
    echo waitress не установлен. Выполни: .venv\Scripts\pip install -r requirements.txt
    pause
)

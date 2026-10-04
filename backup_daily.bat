@echo off
rem Ежедневный бэкап базы расписания (запускается планировщиком задач Windows).
rem Регистрация задачи (один раз, из cmd):
rem   schtasks /Create /SC DAILY /ST 03:00 /TN "TFCSU_Schedule_Backup" /TR "D:\CSU_Chelgu\Schedule\Расписание\backup_daily.bat"
rem Лог пишется в backups\backup_task.log

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" manage.py backup_db >> backups\backup_task.log 2>&1
) else (
    python manage.py backup_db >> backups\backup_task.log 2>&1
)

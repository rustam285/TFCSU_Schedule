@echo off
chcp 65001 >nul
rem Разовая установка зависимостей парсера. Выполнять после изменения
rem requirements.txt (при каждом запуске парсера это делать НЕ нужно).
rem
rem ВАЖНО: Python не новее 3.13. Для Python 3.15 нет готовых wheel-ов
rem pydantic-core, и pip пытается собирать их из исходников компилятором
rem (Rust/MSVC), которого на сервере нет - установка падает с ошибками
rem "link.exe not found" / "Microsoft Visual C++ 14.0 or greater is required".

cd /d "%~dp0"
pip install -r requirements.txt
echo.
echo Если выше были ошибки сборки - Python слишком новой версии, поставь 3.12 или 3.13.
pause

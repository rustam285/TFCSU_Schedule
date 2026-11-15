# Перенос сайта расписания на сервер (Windows) — пошаговая инструкция

Сайт: `tfcsu.ru:8100`. Ниже — полный путь с твоего рабочего компьютера на сервер.
Команды выполняются в **командной строке** (cmd) или PowerShell.

---

## Часть 1. Подготовка на твоём компьютере

**Шаг 1.1.** Открой папку проекта `Расписание` и убедись, что всё работает локально
(`.venv\Scripts\python manage.py runserver`).

**Шаг 1.2. Скопируй на сервер** (флешка/RDP-буфер/сетевая папка — что доступно)
папку проекта **целиком**, КРОМЕ:

- `.venv\` — виртуальное окружение привязано к твоему компьютеру, на сервере создадим новое;
- `staticfiles\` — сгенерируется на сервере командой collectstatic;
- `__pycache__\` (если вдруг попадётся) — мусор.

**Обязательно должны быть скопированы:**

- все `.py`-файлы и папки `main\`, `djangoProject\`, `schedule-parser\`;
- `requirements.txt`, `manage.py`, `backup_daily.bat`, `запуск_сервера.bat`, `DEPLOY.md`;
- **`db.sqlite3` — это вся база расписания** (преподаватели, группы, пары, админы);
- `backups\` — резервные копии базы;
- `main\static\` и `main\templates\`.

Пусть на сервере проект ляжет, например, в `C:\Schedule\` (ниже в командах используется
этот путь — подставь свой, если другой).

---

## Часть 2. Установка на сервере

**Шаг 2.1. Python.** Если на сервере ещё нет Python — скачай и установи
Python 3.12 или 3.13 с python.org. При установке ОБЯЗАТЕЛЬНО поставь галочку
**"Add Python to PATH"**. Проверь в cmd:

```
python --version
```

**Шаг 2.2. Окружение и библиотеки.** В cmd на сервере:

```
cd C:\Schedule
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Зависимости **парсера** ставятся отдельно (парсер работает на системном Python,
не в .venv) — один раз:

```
cd C:\Schedule\schedule-parser
install.bat
```

Важно: Python на сервере — не новее 3.13. Для 3.15 нет готовых wheel-ов
pydantic-core, и установка падает с ошибками сборки («link.exe not found»,
«Microsoft Visual C++ 14.0 required»).

**Шаг 2.3. Настройки сервера: файл `server_env.bat` (один раз).**

Секреты и прод-настройки сайт берёт из ЛОКАЛЬНОГО файла `server_env.bat` —
`запуск_сервера.bat` сам читает его при старте. **Не задавай их через setx**:
setx кладёт переменные в окружение пользователя, а сайт запускается
планировщиком от имени SYSTEM и этих переменных не видит. Из-за этого сайт
однажды стартовал без секретного ключа — в логах сыпались «Session data
corrupted», у пользователей слетали входы, а ALLOWED_HOSTS пришлось
хардкодить прямо в settings.py.

1. Скопируй шаблон: `copy server_env.bat.example server_env.bat`
2. Сгенерируй ключ:
   `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
3. Вставь ключ в `server_env.bat` (строка `set DJANGO_SECRET_KEY=...`) и проверь
   соседние строки: `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS=tfcsu.ru,localhost,127.0.0.1`

`server_env.bat` не коммитится в git (он в .gitignore) и хранится только на сервере.
Если ключ на сервере раньше менялся или терялся, разово вычисти все старые сессии
(пользователям придётся просто войти заново):

```
cd C:\Schedule
.venv\Scripts\python.exe manage.py shell -c "from django.contrib.sessions.models import Session; Session.objects.all().delete()"
```

(иначе в логах до двух недель будут предупреждения «Session data corrupted»,
пока старые сессии не истекут сами).

**Шаг 2.4. Статика.** Whitenoise уже встроен в проект, статика складывается так:

```
cd C:\Schedule
.venv\Scripts\python.exe -m django collectstatic --settings=djangoProject.settings --noinput
```

**Шаг 2.5. Проверка перед запуском.**

```
.venv\Scripts\python.exe -m django check --settings=djangoProject.settings
```

Должно быть: `System check identified no issues`.

Миграции применять НЕ нужно — база `db.sqlite3` уже перенесена вместе с проектом.
(Если в будущем появятся новые миграции — `... -m django migrate --settings=...`.)

**Шаг 2.6. Первый запуск.**

```
запуск_сервера.bat
```

Открой на сервере браузер: `http://127.0.0.1:8100` — сайт должен открыться.
Снаружи: `http://tfcsu.ru:8100`. Учётки админов те же, что были в базе.

Если сайт снаружи не открывается — на сервере/маршрутизаторе должен быть открыт
(проброшен) порт 8100 — это сетевая настройка, обычно уже сделана, раз сайт там работал.

**Шаг 2.7. Автозапуск сайта (чтобы переживал перезагрузки сервера).**
Зарегистрируй задачу планировщика (один раз, cmd от администратора):

```
schtasks /Create /TN "TFCSU_Schedule_Site" /SC ONSTART /RU SYSTEM /TR "C:\Schedule\запуск_сервера.bat"
```

Теперь сайт стартует сам при включении сервера. Проверить/остановить/удалить задачу:

```
schtasks /Query /TN "TFCSU_Schedule_Site"
schtasks /End    /TN "TFCSU_Schedule_Site"
schtasks /Delete /TN "TFCSU_Schedule_Site"
```

**Шаг 2.8. Ежедневный бэкап (планировщик).**

```
schtasks /Create /SC DAILY /ST 03:00 /TN "TFCSU_Schedule_Backup" /TR "C:\Schedule\backup_daily.bat"
```

Лог задачи пишется в `backups\backup_task.log`.

**Шаг 2.9. Куда пишутся логи.**

- `C:\Schedule\logs\site.log` — весь вывод сайта (waitress): старты, остановки с кодом
  ошибки, запросы, падения;
- `C:\Schedule\schedule-parser\logs\parser.log` — весь вывод парсера;
- `C:\Schedule\logs\django.log` — предупреждения и ошибки Django (ротация: 5 МБ × 3 файла).

Если сайт или парсер упадёт, его консольное окно **не закрывается**: в нём остаётся
код ошибки и последние ~30 строк лога. При разборе инцидентов («упало, а что случилось —
непонятно») смотри эти файлы.

---

## Часть 3. Обновление сайта в будущем

Когда внесёшь изменения на своём компьютере и захочешь перенести их на сервер:

1. На сервере останови сайт: `schtasks /End /TN "TFCSU_Schedule_Site"` (или закрой окно bat).
2. Скопируй на сервер изменённые файлы (обычно `main\`, `djangoProject\`, шаблоны, батники).
   **Не перезаписывай `db.sqlite3`, если на сервере в базу уже вносили правки** —
   на сервере база актуальнее твоей локальной!
   `settings.py` на сервере должен совпадать с репозиторием (прод-настройки берутся из
   `server_env.bat`, а не из кода).
3. Если менялся `requirements.txt`: `.venv\Scripts\pip install -r requirements.txt`.
   Если менялся `schedule-parser\requirements.txt`: запусти `schedule-parser\install.bat`.
4. Если есть новые миграции: `.venv\Scripts\python.exe -m django migrate --settings=djangoProject.settings`.
5. Пересобери статику: `... -m django collectstatic --settings=djangoProject.settings --noinput`
   (обязательно после правок JS/CSS — без пересборки сайт продолжит отдавать старые файлы).
6. Запусти сайт снова: `schtasks /Run /TN "TFCSU_Schedule_Site"` (или `запуск_сервера.bat`).

---

## Часть 4. Резервные копии: где лежат и как восстанавливать

### Где лежат
Папка `backups\` рядом с `db.sqlite3` (на сервере — `C:\Schedule\backups\`).
Имена файлов: `db_backup_2026-09-10_21-24-47_manual.sqlite3` (дата-время + метка:
`manual` — создан кнопкой в админке, `import` — автоматически перед импортом расписания).

### Как создать
- кнопкой: админка → «Резервные копии» → «Создать бэкап сейчас»;
- перед каждым импортом расписания — создаётся сам;
- раз в сутки планировщиком (`backup_daily.bat`, см. Шаг 2.8);
- вручную: `.venv\Scripts\python.exe -m django backup_db --settings=djangoProject.settings`.

### Как скачать на свой компьютер
Админка → «Резервные копии» → кнопка «Скачать» у нужного файла.
Бэкап — это один файл, полноценная копия всей базы.

### Как восстановить базу из бэкапа
Бэкап — готовый файл базы, «загружать» его в систему не нужно: он просто заменяет текущую базу.

1. Останови сайт: `schtasks /End /TN "TFCSU_Schedule_Site"` (или закрой окно bat).
2. На всякий случай сохрани текущую базу: `copy C:\Schedule\db.sqlite3 C:\Schedule\backups\db_before_restore.sqlite3`
3. Замени базу бэкапом (подставь имя нужного файла):

```
copy /Y C:\Schedule\backups\db_backup_2026-09-10_21-24-47_manual.sqlite3 C:\Schedule\db.sqlite3
```

4. Запусти сайт: `schtasks /Run /TN "TFCSU_Schedule_Site"`.

Если бэкап лежит не в папке `backups`, а, например, скачан на рабочий стол —
сначала скопируй его в `C:\Schedule\backups\` (или сразу командой copy по его полному пути).

### Перенос базы между компьютером и сервером
База = один файл `db.sqlite3`. Перенести данные = скопировать этот файл
(сайт на время копирования лучше остановить, чтобы файл не менялся в процессе).
Перед экспериментами на своём компьютере можешь накатить свежую серверную базу себе
и наоборот — актуальную локальную на сервер (останавливая сайт и заменяя файл, как выше).

---

## Локальный запуск (на твоём компьютере)

Ничего не меняется: `python manage.py runserver` работает с дефолтами
(DEBUG=True, localhost). Окружение проекта: `.venv`
(`python -m venv .venv` + `.venv\Scripts\pip install -r requirements.txt`).

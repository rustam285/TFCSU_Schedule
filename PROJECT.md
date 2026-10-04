# PROJECT.md — сайт расписания Троицкого филиала ЧелГУ

Документ для ИИ-агента: прочти его целиком перед работой с проектом.
Здесь — структура, назначение файлов, доменная логика, развёртывание и подводные камни.

---

## 1. Что это за проект

Веб-сайт расписания учебных занятий Троицкого филиала ЧелГУ.

- **Стек сайта:** Django 5.1 + SQLite (`db.sqlite3`), Bootstrap 5 + jQuery + select2 (все библиотеки локально в `main/static`), waitress на проде, whitenoise для статики.
- **Стек парсера:** отдельное FastAPI-приложение в `schedule-parser/` (свой venv не имеет, ставится системным pip; см. раздел 9).
- **Пользователи:** стандартная модель `django.contrib.auth.models.User`, ролей/групп нет. Гость видит страницы просмотра; залогиненный — админ-панель (`/admin/...`), уведомления и экспорт.
- **Это НЕ git-репозиторий** — историю изменений не спросить у git, ориентируйся на этот файл, README.md, DEPLOY.md и папки «для копирования N».
- Рабочая ОС — Windows (сервер и локальная машина). Пути с пробелами/кириллицей — всегда в кавычках. Оболочка может быть cmd или Git Bash — проверяй синтаксис.

## 2. Запуск

| Команда | Что делает |
|---|---|
| `запуск_локально.bat` | локально: pip install, пытается запустить парсер (упадёт из-за IP сервера, см. раздел 9), `manage.py runserver` (127.0.0.1:8000) |
| `запуск_сервера.bat` | прод: waitress на 0.0.0.0:8100 (+инструкции по первому запуску в шапке файла) |
| `запуск_на_сервер.bat` | полный запуск на сервере: pip install, парсер, `runserver 192.168.2.250:8100` |
| `.venv\Scripts\python.exe -m django <команда> --settings=djangoProject.settings` | формат запуска management-команд (всегда с явным settings) |

Настройки через переменные окружения (см. `djangoProject/settings.py`):
`DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (по умолчанию True), `DJANGO_ALLOWED_HOSTS`
(по умолчанию `tfcsu.ru,localhost,127.0.0.1`).

## 3. Структура корня

```
├── manage.py, db.sqlite3          # сайт и его база
├── djangoProject/                 # настройки (settings/asgi/wsgi/urls)
├── main/                          # всё приложение (см. раздел 5)
├── schedule-parser/               # отдельный FastAPI-парсер расписаний (раздел 9)
├── requirements.txt               # зависимости сайта (в venv .venv)
├── staticfiles/                   # STATIC_ROOT (collectstatic)
├── backups/ + backup_daily.bat    # резервные копии базы (раздел 8.4)
├── для копирования 3/4/5/         # наборы файлов для переноса на сервер (раздел 11)
├── Тесты экспорта/                # файлы, выгруженные пользователем для сверки
├── Тестовое расписание для проверок/
├── README.md, DEPLOY.md           # документация по развёртыванию (актуальна)
└── запуск_*.bat
```

## 4. Доменная логика (главное!)

**Пары (Lesson).** Номера пар: 1, 2, 2.5 («ЭКЗ», экзаменационный слот), 3–8.
Время пар — в `main/forms.py`, класс `LessonForm`:
`1: 8:00-9:30, 2: 9:40-11:10, 2.5: 10:00, 3: 11:20-12:50, 4: 13:15-14:45, 5: 15:00-16:30, 6: 16:40-18:10, 7: 18:20-19:50, 8: 19:55-21:25`.
`LessonForm.week_day` — порядок дней `пн..вс`, `NUMBER_OF_LESSON_CHOICES` — подписи номеров.

**Два вида расписания:**
- `ConstantSchedule` — постоянное (недельная сетка): день недели + номер недели (1 или 2);
- `TemporarySchedule` — замены на конкретную дату.

**Чётность недель** (`main/services/util.py`): `get_week_number(date)` считает 1/2 от начала
учебного года (`get_academic_year_beginning_date()` — 1 сентября, сдвигается на понедельник).

**Правила отображения дисциплин** (`TeacherDisciplineRule`): для преподавателя можно
«показывать дополнительно» или «скрывать» дисциплины; для гостей действуют только правила
с галочкой `apply_for_guests`. Применяются в `constant_schedule_service` при построении
расписания преподавателя.

**Дни/недели при просмотре:** страницы гостей строятся от диапазона дат; админская страница
`/admin/schedule/group/` — чекбоксы дней + недель с переключателями «Все дни»/«Все недели»
(пустой выбор → ошибка; сервер понимает `all_days=1`/`all_weeks=1` и списки `chosen_day`/`chosen_week`).

## 5. Приложение main

```
main/
├── models.py          # все модели (см. 5.1)
├── urls.py            # все маршруты сайта
├── constants.py       # наборы кнопок для главной админки (label, url, disabled)
├── forms.py           # LessonForm (время пар!) + ModelForm-ы справочников
├── middleware.py      # LoginRequiredMiddleware: всё /admin/* → login/?next=...
├── backup.py          # create_backup() — копия базы перед импортом
├── views/             # по файлу на раздел (см. 5.2)
├── services/          # вся работа с БД — ТОЛЬКО здесь (см. 5.3)
├── templates/main/    # страницы; вложенные папки guest/, teacher/, notifications/,
│                      #   schedule_import/, faculty/, group/, discipline/, auditorium/
├── templates/components/  # inclusion-теги: search_form, pagination, modal,
│                      #   forms/, tables/ (в т.ч. admin_schedule_table, schedule_table_*)
├── templatetags/template_tags.py  # все inclusion-теги (render_*)
├── static/            # css/js/Images (bootstrap, jquery, select2, csu.css — фирменные цвета)
└── management/commands/backup_db.py  # python manage.py backup_db — ручной бэкап
```

### 5.1. Модели

| Модель | Назначение |
|---|---|
| `Faculty` | направление (факультет) |
| `Group` | группа: форма обучения `о` / `з` / `о-з`, курс, факультет |
| `Teacher` | преподаватель: `name` («Фамилия И.О.»), `title` (звание) |
| `Discipline` | дисциплина, m2m на преподавателей |
| `Auditorium` | `building` (корпус), `number` (номер) |
| `Lesson` | пара: номер, `is_special` (спецобъявление → `*`), дисциплина, формат (лекция/пз…), преподаватель, аудитория, группа |
| `ConstantSchedule` | Lesson + день недели + номер недели (1\|2) |
| `TemporarySchedule` | Lesson + дата |
| `TeacherDisciplineRule` | показывать/скрывать дисциплину у преподавателя |
| `NotificationSubscription` | подписка на уведомления (см. 8.2) |
| `SiteSetting` | key-value, хранит `updated_at` (дата изменения расписания) |

### 5.2. Views (main/views/)

| Файл | Что в нём |
|---|---|
| `guests_views.py` | гостевые страницы: главная, расписание по группам/преподавателям/аудиториям (диапазон дат) |
| `admin_views.py` | главная админки; **просмотр по группе** (`render_schedule_by_group_page` + `return_fields_for_choice`/`add_table_data` — чекбоксы дней/недель); просмотр по преподавателям/аудиториям |
| `schedule_views.py` | добавление/изменение/удаление/импорт расписания очной формы |
| `part_time_schedule_views.py`, `mixed_schedule_views.py` | то же для заочной и очно-заочной |
| `teachers_views.py`, `group_views.py`, `faculty_view.py`, `auditory_views.py`, `discipline_views.py` | CRUD справочников (поиск `q`, пагинация 25/стр) |
| `teacher_rule_views.py` | правила отображения дисциплин (эталон «страницы настроек») |
| `notification_views.py` | страницы настройки уведомлений + JSON `/notifications/data/` |
| `export_views.py` | `/export/schedule/?type=group\|teacher\|auditorium&id=..&format=xlsx\|docx\|pdf` |
| `database_views.py` | `/export/` — полная база в Excel (pandas) |
| `backup_views.py` | страница резервных копий + скачивание |
| `auth_views.py` | вход/выход |

Паттерн страниц: GET-параметры (`chosen_*`) + POST-обработка в том же view + PRG-редирект +
сообщения через `django.contrib.messages` (в шаблонах цикл `alert-{{ message.tags }}`,
ERROR маппится на `danger`). Списки: `render_search_form` + `render_pagination` + таблицы-теги.

### 5.3. Services (main/services/)

| Файл | Что в нём |
|---|---|
| `util.py` | даты, чётность недель, `get_data_for_schedule`, `updated_at`, `get_error_messages` |
| `constant_schedule_service.py` | запросы постоянного расписания: `get_const_schedule_by_date` (учёт правил преподавателя), `get_temp_schedule_by_date`, `union_const_and_temp_schedule_by_date`, `get_table_query_for_{group,teacher,auditorium}_by_dates`, `get_query_for_table(group, 'пн ср', '1 2')` — дни/недели строкой через пробел |
| `temporary_schedule_service.py` | замены, `get_query_for_table_by_dates` |
| `group_service.py`, `teacher_service.py`, `auditorium_service.py`, `discipline_service.py`, `faculties_service.py`, `lesson_service.py` | тонкие обёртки CRUD |
| `validation_service.py` | валидация дат/импорта (бросает ValidationError со списком сообщений) |
| `teacher_rule_service.py` | правила дисциплин, `get_filtered_discipline_ids` |
| `notification_service.py` | уведомления (см. 8.2) |
| `export_service.py` | экспорт в xlsx/docx/pdf (см. 8.1) |

### 5.4. Шаблоны и UI-каркас

`base.html` — общий каркас:
- бордовая шапка `.csu`; для залогиненных справа: колокольчик уведомлений + «Выйти»;
- под шапкой — полоса с бургером; **левый сайдбар** `#admin-sidebar` (меню администратора:
  Расписание / Просмотр / Импорт / Справочники / Сервис — на инлайн-стилях + `<style>`);
- **правая шторка** `#notifications-panel` (уведомления) — зеркало сайдбара, панели закрывают
  друг друга (глобальные `closeAdminSidebar()`/`closeNotifications()`);
- в конце — глобальная инициализация `$('.select2').select2()`;
- гости видят только шапку с «Войти»; залогиненные — шапку с колокольчиком и бургер на всех страницах.

Фирменные цвета: бордовый `#6f0724` (шапка), тёмный `#380216` (рамки/ссылки), кнопки `btn-danger`.

### 5.5. Маршруты (main/urls.py, только имена)

Гостям: `guests`, `guests_check_groups`, `guests_check_preps`, `guests_check_auds`.
Вход: `login`, `logout`.
Админка (`/admin/...`, закрыты middleware): `home`, CRUD-страницы справочников
(`teachers/add_teachers/...`, `groups`, `faculty`, `auditory`, `discipline`),
расписания (`schedule`, `edit_schedule`, `delete_schedule`, `for_edit_lesson`,
`import_schedule`, `add_part_time_schedule`, `edit_part_time_lesson`, `import_part_time_schedule`,
`delete_part_time_schedule`, `add_mixed_schedule`, `edit_mixed_schedule`, `edit_mixed_lesson`,
`import_mixed_schedule`, `delete_mixed_schedule`), просмотр (`check_schedule_group`,
`check_schedule_teachers`, `check_schedule_auditoriums`), `teacher_rules`, `backups`/`download_backup`,
уведомления (`notification_settings`, `notification_teachers`, `notification_auditoriums`,
`notification_teacher_settings`, `notification_auditorium_settings`).
Вне /admin/: `export_excel` (`/export/`), `export_schedule` (`/export/schedule/`), `notifications_data` (`/notifications/data/`).

## 6. Настройки и развёртывание

- Прод: waitress (`запуск_сервера.bat`, порт 8100), whitenoise, `DJANGO_DEBUG=False`,
  `DJANGO_SECRET_KEY` и `DJANGO_ALLOWED_HOSTS` заданы на сервере (см. DEPLOY.md).
- Статика: `collectstatic` в `staticfiles/` (нужен, только если менялись файлы в `main/static`).
- Обновление на сервере — через **папки «для копирования N»** (раздел 11): скопировать поверх
  с сохранением структуры, при необходимости `pip install -r requirements.txt` / `migrate`, перезапустить.
- Бэкапы: `python manage.py backup_db`, `backups/`, ежедневный `backup_daily.bat`;
  перед импортом расписания вызывается `create_backup()` автоматически.

## 7. Зависимости сайта (requirements.txt)

`django~=5.1.2`, `django-select2~=8.2.1`, `pandas`, `openpyxl` (Excel),
`whitenoise`, `waitress`, `python-docx~=1.2.0` (Word), `reportlab~=5.0.1` (PDF).

## 8. Ключевые фичи (сделаны в сессиях, подробности — в коде)

### 8.1. Экспорт расписания (`export_service.py`, `export_views.py`)
- Официальный бланк «сетка семестра»: заголовок «Расписание группы X (форма обучения)» /
  «N семестр ГГГГ-ГГГГ учебного года» (семестр — `get_semester_info()`), сетка «дни × пары»,
  недели 1 и 2 рядом, у субботы и воскресенья пары 1–5 (6-я добавится, если есть занятия),
  шрифт Times New Roman, книжная ориентация A4.
- Имена файлов: `ТФИ-401_26-27.xlsx` (группа + учебный год), `Преподаватель_Фамилия_И.О._26-27`,
  `Аудитория_214_26-27`.
- У преподавателя одинаковые занятия разных групп склеиваются; у аудитории — сетка из 5 колонок
  («Дисциплина (формат), преподаватель — группы»).
- **Строится только по ConstantSchedule** (замены не входят).
- Word: авто-подбор шрифта (9→4,5 pt) + фиксированные высоты строк → всегда одна страница;
  PDF: класс `_FitToPageTable` масштабирует таблицу целиком → всегда одна страница;
  Excel: поворот дней на 90°, ширины колонок как в бумажном бланке.
- Кнопки — на гостевых страницах под таблицей; в админке — кнопка «Получить PDF»
  на `/admin/schedule/group/`.
- PDF-шрифт: системный `C:\Windows\Fonts\times.ttf` (фолбэки — arial, tahoma, dejavu).

### 8.2. Уведомления (`NotificationSubscription`, `notification_service.py`, `notification_views.py`)
- Только для залогиненных. Колокольчик в шапке + правая шторка: уведомления с сегодня до
  воскресенья (если сегодня воскресенье — следующая неделя, `get_notification_week_dates`).
- Подписка = преподаватель ИЛИ аудитория + режим: `default` (сегодня/завтра), `dates`
  (конкретные даты, JSON в `dates`), `weekdays` (дни 1/2-й недели, JSON `'1-пн'` в `week_days`).
  Добавление даты/сохранение дней авто-переключает режим. Уведомление только если есть пара
  (постоянное + замены; для преподавателя — с правилами дисциплин). Одинаковые дисциплины
  нескольких групп = одна пара (группы через запятую).
- Настройка: `/admin/notifications/` → списки с поиском/пагинацией → страница подписки.
- JSON: `/notifications/data/` → `{count, groups:[{date, title, entries:[{kind,name,lessons}]}]}`.

### 8.3. Просмотр `/admin/schedule/group/`
Чекбоксы дней (7) и недель (2) + «Все дни»/«Все недели» (свежая страница — оба отмечены);
скрытое поле `form_submitted` отличает «ещё не отправляли» от «отправили пустым» (пустое →
сообщение об ошибке). Заочные группы — диапазон дат. Кнопка «Получить PDF» → экспорт группы.

## 9. schedule-parser (отдельный сервис)

- FastAPI + uvicorn, порт 8001: парсит xlsx-файлы расписаний (очная — `he_parser_service`,
  заочная — `part_time_parser_service`, све — `sve_parser_service`; модели в `app/service/model`,
  роуты в `app/web/router/scheduler_parser_routes.py`).
- Свой `requirements.txt` (fastapi, uvicorn, pydantic, xlrd), ставится системным pip
  (`start.bat`: pip install + python main.py).
- **Внимание:** в `schedule-parser/main.py` хост захардкожен `192.168.2.250` (IP сервера) —
  локально падает с WinError 10049. Локально запускать, поменяв на `0.0.0.0`/`127.0.0.1`.
- Сайт к парсеру по сети НЕ обращается (импорт работает через страницы импорта сайта).

## 10. Тестирование и проверки

- Штатных тестов нет (`main/tests.py` пуст). Проверка — временными скриптами через
  `.venv\Scripts\python.exe` + `django.test.Client`. **Обязательно:**
  `from django.test.utils import setup_test_environment; setup_test_environment()` — иначе
  400 из-за хоста `testserver` (нет в ALLOWED_HOSTS).
- В скриптах на Windows: `sys.stdout.reconfigure(encoding='utf-8')` для кириллицы.
- Проверка страниц гостя анонимно: `/admin/*` → редирект на `/login/`.
- `python -m django check --settings=djangoProject.settings` — быстрая проверка целостности.
- Временные скрипты (test_*.py, debug_*.py, repro_*.py) по окончании удалять.

## 11. Механизм обновлений: «для копирования N»

Сервер обновляется копированием файлов из папок `для копирования N` (по одной на пакет
изменений; архивы `.zip` — те же папки). Состав и порядок установки — в `ИНСТРУКЦИЯ.md`
внутри каждой папки. Установлены/готовы:

| Папка | Что добавляет | Требует |
|---|---|---|
| 3 | Экспорт расписания (xlsx/docx/pdf, сетка семестра) + библиотеки python-docx, reportlab | — |
| 4 | Уведомления (+модель, миграция `0027_notificationsubscription`, migrate обязателен) | 3 |
| 5 | Чекбоксы дней/недель и «Получить PDF» на `/admin/schedule/group/`, «Правила предметов» в «Сервисе» | 3, 4 |

При новых изменениях — создавай следующую папку с тем же принципом
(файлы с сохранением структуры + ИНСТРУКЦИЯ.md + отметить, нужен ли pip/migrate/collectstatic).

## 12. Подводные камни (важно!)

- **Не git** — перед изменениями нечем «посмотреть diff»; аккуратнее с правками, ориентируйся на этот файл.
- Обновление затирает файлы целиком: правя файл, помни, что в нём уже живут фичи из всех папок N.
- reportlab 5: `longTableOptimize=1` по умолчанию — при отрисовке таблицы целиком после
  `wrap()` с ограниченной высотой падает KeyError в `_spanRects` (в `export_service` обойдено:
  высота считается с `wrap(…, 10**6)`).
- Word/PDF экспорт «в одну страницу» — фиксированные высоты строк (docx) и масштабирование
  (pdf); при изменении ширины колонок (`DOCX_COLUMN_WIDTHS`, `PDF_COLUMN_WIDTHS`) проверяй,
  что сумма ≤ ~19 см.
- `Content-Disposition` с кириллицей — двойной формат: ASCII-фолбэк + `filename*=UTF-8''…`.
- Ссылки на экспорт в шаблонах пишутся с обычным `&` (Django не экранирует литеральный текст).
- select2 глобально инициализируется в `base.html`; класс `.select2` на селектах достаточен.
- `message_constants.DEBUG: 'debug'` и ERROR→`danger` — в settings (шаблоны используют `alert-{{ message.tags }}`).
- Кодировка файлов — UTF-8; в Windows-консоли для кириллицы нужен `chcp 65001` или reconfigure.

## 13. Хронология изменений (кратко)

1. Базовый сайт расписания (до этой документации) — просмотр, справочники, импорт, бэкапы.
2. «для копирования 3»: экспорт группы/преподавателя/аудитории в Word/Excel/PDF (бланк семестра,
   одна страница, вертикальные дни, склейка одинаковых дисциплин).
3. «для копирования 4»: система уведомлений (подписки, три режима, шторка справа, колокольчик);
   фиксы: значения радио-режимов, склейка дисциплин, авто-переключение режима.
4. «для копирования 5»: мультивыбор дней/недель чекбоксами + «Все дни»/«Все недели»,
   кнопка «Получить PDF» на просмотре по группе, «Правила предметов» → карточка «Сервис».

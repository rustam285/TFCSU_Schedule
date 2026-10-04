import datetime
import json
from main.forms import LessonForm
from main.services import group_service, teacher_service, auditorium_service


def reformat_date_string(db_string_date: str) -> str:
    return datetime.datetime.strptime(db_string_date, "%Y-%m-%d").strftime("%d.%m.%Y")


def get_error_messages(e: Exception) -> list[str]:
    """Список сообщений об ошибке: у ValidationError это messages, у остальных — str(e)."""
    if hasattr(e, 'messages'):
        return list(e.messages)
    return [str(e)]


def normalize_search_query(value: str) -> str:
    """Нормализация строки для поиска: без учёта регистра и без разницы е/ё.

    «Еремкин» и «Ерёмкин» дают одинаковый результат."""
    return (value or '').casefold().replace('ё', 'е')


def filter_by_query(objects: list, query: str, key) -> list:
    """Фильтрация списка по запросу без учёта регистра и разницы е/ё.

    SQLite (LIKE) не умеет этого для кириллицы, поэтому фильтруем в Python —
    справочники маленькие, вывозить на страницу всё равно приходится.
    key — функция, возвращающая строку для поиска у объекта (lambda t: t.name)."""
    q = normalize_search_query(query)
    if not q:
        return objects
    return [obj for obj in objects if q in normalize_search_query(key(obj))]


def convert_string_to_date(date):
    return datetime.datetime.strptime(date, "%Y-%m-%d")


def convert_schedule_string_to_date(date):
    return datetime.datetime.strptime(date, "%d.%m.%Y")


def convert_date_to_string(date):
    return date.strftime("%Y-%m-%d")


def get_data_for_schedule():
    return {
        'full_time_groups': group_service.get_by_form_of_education('о'),
        'part_time_groups': group_service.get_by_form_of_education('з'),
        'mixed_groups': group_service.get_by_form_of_education('о-з'),
        'numbers': LessonForm().NUMBER_OF_LESSON_CHOICES.items(),
        "week_numbers": LessonForm().week_number,
        "week_days": LessonForm().week_day,
        'teachers': teacher_service.get_all(),
        'auditoriums': auditorium_service.get_all()
    }


def get_today_date():
    today = datetime.date.today()
    if today.isoweekday() == 7:
        today += datetime.timedelta(days=1)
    return today.strftime("%Y-%m-%d")


def get_next_date():
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    if tomorrow.isoweekday() == 7:
        tomorrow += datetime.timedelta(days=1)
    return tomorrow.strftime("%Y-%m-%d")


def get_weekday_by_date(date):
    return date.weekday()


def _read_updated_at_from_file() -> str | None:
    """Старое место хранения даты — static/json. Используется только один раз,
    чтобы перенести значение в базу при первом обращении."""
    try:
        with open('main/static/json/updated_at.json') as json_data:
            return json.load(json_data)["statistic"]["updated_at"]
    except (OSError, KeyError, ValueError):
        return None


def update_updated_at_json():
    """Записывает текущие дату и время как «последнее изменение расписания» (в базу).

    Имя историческое (раньше писала в json-файл) — оставлено, чтобы не менять
    вызовы в views и сигналах.
    """
    from django.utils import timezone

    from main.models import SiteSetting
    SiteSetting.objects.update_or_create(
        key='updated_at',
        defaults={'value': timezone.localtime().strftime('%d.%m.%Y %H:%M')},
    )


def touch_updated_at(sender, **kwargs):
    """Обработчик сигнала сохранения/удаления занятия: обновляет глобальную
    дату последнего изменения расписания и дату группы этого занятия.

    Важно: функция обязана жить на уровне модуля, а не внутри AppConfig.ready().
    connect() держит обработчик по слабой ссылке — локальная функция из ready()
    собирается сборщиком мусора, и сигнал молча перестаёт работать.
    """
    update_updated_at_json()
    instance = kwargs.get('instance')
    if instance is not None and getattr(instance, 'group_id', None):
        touch_group_updated_at(instance.group_id)


def touch_group_updated_at(group_id):
    """Отмечает «сейчас» как дату последнего изменения расписания группы."""
    from django.utils import timezone

    from main.models import Group
    # .update(), а не save(): без дополнительных сигналов и запросов
    Group.objects.filter(pk=group_id).update(updated_at=timezone.now())


def get_updated_at_from_json() -> str:
    """Дата последнего изменения расписания из базы; при первом обращении
    значение переносится из старого json-файла (или берётся сегодняшняя дата)."""
    from main.models import SiteSetting
    setting, _ = SiteSetting.objects.get_or_create(
        key='updated_at',
        defaults={'value': _read_updated_at_from_file() or reformat_date_string(get_today_date())},
    )
    return setting.value


def get_academic_year_beginning_date() -> datetime.date:
    today = datetime.date.today()
    result_year = today.year - 1 if today.month in range(1, 9) else today.year
    result_date = datetime.date(result_year, 9, 1)
    if result_date.isoweekday() in [6, 7]:
        while result_date.isoweekday() != 1:
            result_date += datetime.timedelta(days=1)

    return result_date


def get_week_number(input_date: datetime.date) -> [1, 2]:
    return (get_academic_year_beginning_date().isocalendar().week - input_date.isocalendar().week) % 2 + 1


def get_current_week_number() -> [1, 2]:
    return (get_academic_year_beginning_date().isocalendar().week - datetime.date.today().isocalendar().week) % 2 + 1


def get_current_week_day():
    return LessonForm().week_day[datetime.date.today().weekday()][0]


def get_dates(start_date: datetime.date, end_date: datetime.date) -> list[datetime.date]:
    days_diff = (end_date - start_date).days
    return [start_date + datetime.timedelta(days=x) for x in range(days_diff + 1)]

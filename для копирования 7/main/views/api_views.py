"""JSON-API для внешних потребителей (VK-бот, мобильные клиенты и т.п.).

Только чтение и только GET: без CSRF-токена, без авторизации
(LoginRequiredMiddleware закрывает только пути /admin/*).

Эндпоинты (см. main/urls.py):
    GET /api/groups/    — список групп для клавиатуры выбора;
    GET /api/schedule/  — расписание группы за диапазон дат.

Формат дат — ГГГГ-ММ-ДД (как на гостевых страницах сайта).
Ошибки возвращаются как {"error": "текст"} с кодом 400/404.
"""
import datetime

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from main.models import Group
from main.services import group_service
from main.services.constant_schedule_service import get_schedule_days_for_api

# Ограничение диапазона дат: расписание на год одним запросом — это
# сотни дней × несколько пар, бот такое всё равно не отправит одним сообщением.
MAX_RANGE_DAYS = 31

# Русские символы в JSON — как есть, а не \u0417\u0430... . Оба варианта валидны
# для любых JSON-парсеров (C# читает и то, и то); этот просто читаемее в браузере/curl.
JSON_DUMPS_PARAMS = {'ensure_ascii': False}


def _error(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({'error': message}, status=status, json_dumps_params=JSON_DUMPS_PARAMS)


def _parse_date(value: str, param_name: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(
            f"Неверный формат параметра {param_name}: «{value}». Ожидается ГГГГ-ММ-ДД, например 2026-10-05")


def _group_updated_at_display(group: Group) -> str | None:
    if not group.updated_at:
        return None
    return timezone.localtime(group.updated_at).strftime('%d.%m.%Y %H:%M')


@require_GET
def api_groups(request):
    """Список всех групп: id, название, форма обучения, курс, факультет,
    дата последнего изменения расписания группы."""
    groups = []
    for group in group_service.get_all():
        groups.append({
            'id': group.pk,
            'title': group.title,
            'form_of_education': group.form_of_education,
            'form_of_education_label': group.get_form_of_education_display(),
            'course': group.course,
            'faculty': group.faculty.title if group.faculty_id else None,
            'updated_at': _group_updated_at_display(group),
        })
    return JsonResponse({'groups': groups}, json_dumps_params=JSON_DUMPS_PARAMS)


@require_GET
def api_schedule(request):
    """Расписание группы за диапазон дат.

    Параметры:
        group_id — обязательный id группы (из /api/groups/);
        date_from, date_to — даты ГГГГ-ММ-ДД; date_to по умолчанию равен date_from,
        date_from по умолчанию — сегодня. Диапазон — не больше MAX_RANGE_DAYS дней.
    """
    group_id = request.GET.get('group_id')
    if not group_id or not group_id.isdigit():
        return _error('Не указан (или не число) обязательный параметр group_id')
    try:
        group = group_service.get_by_pk(int(group_id))
    except Group.DoesNotExist:
        return _error(f'Группа с id={group_id} не найдена', status=404)

    try:
        date_from_raw = request.GET.get('date_from') or datetime.date.today().strftime('%Y-%m-%d')
        date_to_raw = request.GET.get('date_to') or date_from_raw
        date_from = _parse_date(date_from_raw, 'date_from')
        date_to = _parse_date(date_to_raw, 'date_to')
    except ValueError as e:
        return _error(str(e))

    if date_from > date_to:
        return _error('date_from больше date_to')
    if (date_to - date_from).days + 1 > MAX_RANGE_DAYS:
        return _error(f'Диапазон не может превышать {MAX_RANGE_DAYS} дней')

    dates = [date_from + datetime.timedelta(days=x) for x in range((date_to - date_from).days + 1)]
    return JsonResponse({
        'group': {
            'id': group.pk,
            'title': group.title,
            'form_of_education': group.form_of_education,
            'form_of_education_label': group.get_form_of_education_display(),
            'course': group.course,
        },
        'date_from': date_from.strftime('%Y-%m-%d'),
        'date_to': date_to.strftime('%Y-%m-%d'),
        'updated_at': _group_updated_at_display(group),
        'days': get_schedule_days_for_api(group.pk, dates),
    }, json_dumps_params=JSON_DUMPS_PARAMS)

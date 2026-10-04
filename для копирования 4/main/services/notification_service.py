"""Логика уведомлений о парах для залогиненных пользователей.

Уведомления вычисляются «на лету» при запросе шторки: фоновые задачи не нужны.
Диапазон — текущая неделя с сегодня до воскресенья; если сегодня воскресенье,
берётся следующая неделя (с понедельника по воскресенье).
"""
import datetime
import json

from main.forms import LessonForm
from main.models import NotificationSubscription
from main.services import teacher_rule_service
from main.services.constant_schedule_service import (
    get_const_schedule_by_date, get_temp_schedule_by_date, union_const_and_temp_schedule_by_date)
from main.services.util import get_week_number, get_weekday_by_date

DAY_KEYS = [day_key for day_key, _ in LessonForm().week_day]  # ['пн', 'вт', ... 'вс']


def parse_iso_date(value) -> datetime.date:
    """Строка 'ГГГГ-ММ-ДД' → date; при ошибке бросает ValueError с понятным текстом."""
    try:
        return datetime.date.fromisoformat(str(value))
    except (ValueError, TypeError):
        raise ValueError('Некорректная дата')


def is_valid_week_day(value) -> bool:
    """Корректна ли запись дня недели вида '1-пн' / '2-ср'."""
    try:
        week, day = str(value).split('-', 1)
        return int(week) in (1, 2) and day in DAY_KEYS
    except (ValueError, AttributeError):
        return False


def get_notification_week_dates(today: datetime.date = None) -> list[datetime.date]:
    """Даты показа уведомлений: сегодня → воскресенье этой недели.

    Если сегодня воскресенье — следующая неделя целиком (пн → вс).
    """
    today = today or datetime.date.today()
    if today.isoweekday() == 7:  # воскресенье — показываем следующую неделю
        return [today + datetime.timedelta(days=offset) for offset in range(1, 8)]
    days_left = 8 - today.isoweekday()  # включая сегодня и воскресенье
    return [today + datetime.timedelta(days=offset) for offset in range(days_left)]


def parse_dates(subscription: NotificationSubscription) -> list[datetime.date]:
    try:
        return [datetime.date.fromisoformat(value)
                for value in json.loads(subscription.dates or '[]')]
    except (ValueError, TypeError):
        return []


def parse_week_days(subscription: NotificationSubscription) -> list[tuple[int, str]]:
    """Список пар (номер недели, ключ дня): [(1, 'пн'), (2, 'ср'), ...]."""
    try:
        raw = json.loads(subscription.week_days or '[]')
        result = []
        for value in raw:
            week, day = value.split('-', 1)
            result.append((int(week), day))
        return result
    except (ValueError, TypeError, AttributeError):
        return []


def subscription_triggers_on(subscription: NotificationSubscription, date: datetime.date,
                             today: datetime.date = None) -> bool:
    """Срабатывает ли подписка на эту дату (наличие пар проверяется отдельно)."""
    today = today or datetime.date.today()
    if subscription.mode == NotificationSubscription.Mode.DEFAULT:
        return date in (today, today + datetime.timedelta(days=1))
    if subscription.mode == NotificationSubscription.Mode.DATES:
        return date in parse_dates(subscription)
    if subscription.mode == NotificationSubscription.Mode.WEEKDAYS:
        week_day = DAY_KEYS[get_weekday_by_date(date)]
        return (get_week_number(date), week_day) in parse_week_days(subscription)
    return False


def _lessons_for_subscription(subscription: NotificationSubscription, date: datetime.date) -> list[dict]:
    """Занятия подписки на дату в виде списка словарей для шаблона шторки.

    Одна и та же дисциплина (с тем же форматом, преподавателем и аудиторией),
    идущая в этот слот у нескольких групп, показывается одной парой —
    группы перечисляются через запятую.
    """
    if subscription.teacher_id:
        shown_ids, hidden_ids = teacher_rule_service.get_filtered_discipline_ids(
            subscription.teacher_id, viewer_is_authenticated=True)
        temp = get_temp_schedule_by_date(date, teacher_id=subscription.teacher_id,
                                         shown_discipline_ids=shown_ids,
                                         hidden_discipline_ids=hidden_ids)
        const = get_const_schedule_by_date(date, teacher_id=subscription.teacher_id,
                                           shown_discipline_ids=shown_ids,
                                           hidden_discipline_ids=hidden_ids)
    elif subscription.auditorium_id:
        temp = get_temp_schedule_by_date(date, auditorium_id=subscription.auditorium_id)
        const = get_const_schedule_by_date(date, auditorium_id=subscription.auditorium_id)
    else:
        return []

    slots = union_const_and_temp_schedule_by_date(temp, const, date).values()
    merged = {}
    for slot in slots:
        key = (slot['lesson_number'], slot['discipline'], slot['format'],
               slot['teacher_name'], slot['teacher_title'], slot['auditorium'])
        merged.setdefault(key, {'slot': slot, 'groups': []})['groups'].append(slot['group'])

    lessons = []
    for data in merged.values():
        slot = data['slot']
        teacher = slot['teacher_name'] or ''
        if teacher and slot['teacher_title']:
            teacher += f", {slot['teacher_title']}"
        lessons.append({
            'number': LessonForm().NUMBER_OF_LESSON_CHOICES[slot['lesson_number']],
            'time': LessonForm().time[slot['lesson_number']],
            'label': f"{slot['discipline']}"
                     f"{' (' + slot['format'] + ')' if slot['format'] else ''}",
            'teacher': teacher,
            'auditorium': slot['auditorium'],
            'group': ', '.join(sorted(set(data['groups']))),
        })
    return lessons


def _date_title(date: datetime.date, today: datetime.date) -> str:
    weekday = LessonForm().week_day[get_weekday_by_date(date)][1]
    formatted = date.strftime('%d.%m')
    if date == today:
        return f'Сегодня, {weekday} ({formatted})'
    if date == today + datetime.timedelta(days=1):
        return f'Завтра, {weekday} ({formatted})'
    return f'{weekday} ({formatted})'


def collect_notifications(user, today: datetime.date = None) -> dict:
    """Уведомления пользователя на неделю: группы по датам + счётчик.

    Формат: {'count': N, 'groups': [{'date': 'ГГГГ-ММ-ДД', 'title': 'Сегодня, ...',
    'entries': [{'kind': 'teacher'|'auditorium', 'name': ..., 'lessons': [...]}]}]}
    """
    today = today or datetime.date.today()
    week_dates = get_notification_week_dates(today)
    subscriptions = NotificationSubscription.objects.filter(user=user) \
        .select_related('teacher', 'auditorium')

    groups = []
    for date in week_dates:
        entries = []
        for subscription in subscriptions:
            if not subscription_triggers_on(subscription, date, today):
                continue
            lessons = _lessons_for_subscription(subscription, date)
            if not lessons:
                continue
            if subscription.teacher_id:
                kind, name = 'teacher', subscription.teacher.name
                extra = subscription.teacher.title or ''
            else:
                kind, name = 'auditorium', f'ауд. {subscription.auditorium.number}'
                extra = f'корпус {subscription.auditorium.building}' \
                    if subscription.auditorium.building else ''
            entries.append({'kind': kind, 'name': name, 'extra': extra, 'lessons': lessons})
        if entries:
            groups.append({'date': date.isoformat(), 'title': _date_title(date, today),
                           'entries': entries})

    return {'count': sum(len(entry['lessons']) for group in groups for entry in group['entries']),
            'groups': groups}

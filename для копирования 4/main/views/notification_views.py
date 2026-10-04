"""Настройка уведомлений (для залогиненных) и JSON-эндпоинт для шторки.

Страницы выбора и списков следуют паттерну остальных страниц админ-панели:
выбор сущности → настройка для конкретного преподавателя/аудитории,
POST-обработка с PRG-редиректом и сообщениями через django.contrib.messages.
"""
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from main.forms import LessonForm
from main.models import Auditorium, NotificationSubscription, Teacher
from main.services import auditorium_service, notification_service, teacher_service
from main.services.util import get_error_messages

PAGE_SIZE = 25


@login_required
def render_notification_choice_page(request):
    """Стартовая страница: выбор между уведомлениями по преподавателям и по аудиториям."""
    counts = {
        'teachers': NotificationSubscription.objects.filter(
            user=request.user, teacher__isnull=False).count(),
        'auditoriums': NotificationSubscription.objects.filter(
            user=request.user, auditorium__isnull=False).count(),
    }
    return render(request, 'main/notifications/NotificationChoicePage.html',
                  context={'counts': counts})


def _subscribed_ids(request, field):
    return set(NotificationSubscription.objects.filter(
        user=request.user, **{f'{field}__isnull': False}).values_list(f'{field}_id', flat=True))


def _render_list_page(request, template, objects, field):
    query = request.GET.get('q', '').strip()
    if query:
        objects = objects.filter(name__icontains=query) if field == 'teacher' \
            else objects.filter(number__icontains=query)
    page_obj = Paginator(objects, PAGE_SIZE).get_page(request.GET.get('page'))
    return render(request, template, context={
        'page_obj': page_obj,
        'query': query,
        'subscribed_ids': _subscribed_ids(request, field),
    })


@login_required
def render_notification_teachers_page(request):
    return _render_list_page(request, 'main/notifications/NotificationTeachersPage.html',
                             teacher_service.get_all(), 'teacher')


@login_required
def render_notification_auditoriums_page(request):
    return _render_list_page(request, 'main/notifications/NotificationAuditoriumsPage.html',
                             auditorium_service.get_all(), 'auditorium')


@login_required
def render_notification_teacher_settings(request, teacher_id):
    teacher = get_object_or_404(Teacher, pk=teacher_id)
    return _render_settings_page(request, teacher=teacher)


@login_required
def render_notification_auditorium_settings(request, auditorium_id):
    auditorium = get_object_or_404(Auditorium, pk=auditorium_id)
    return _render_settings_page(request, auditorium=auditorium)


def _get_subscription(user, teacher=None, auditorium=None):
    return NotificationSubscription.objects.filter(
        user=user, teacher=teacher, auditorium=auditorium).first()


def _save_dates(subscription, dates):
    subscription.dates = json.dumps(sorted({date.isoformat() for date in dates}))


def _save_week_days(subscription, week_days):
    subscription.week_days = json.dumps(sorted(set(week_days)))


def _render_settings_page(request, teacher=None, auditorium=None):
    """Настройка подписки для конкретного преподавателя или аудитории."""
    subscription = _get_subscription(request.user, teacher, auditorium)

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'delete':
                if subscription:
                    subscription.delete()
                    messages.success(request, 'Уведомления отключены')
                else:
                    messages.error(request, 'Подписка не была настроена')
            elif action == 'save_mode':
                mode = request.POST.get('mode')
                if mode not in NotificationSubscription.Mode.values:
                    raise ValueError('Некорректный режим уведомлений')
                if subscription is None:
                    subscription = NotificationSubscription(
                        user=request.user, teacher=teacher, auditorium=auditorium, mode=mode)
                else:
                    subscription.mode = mode
                subscription.save()
                messages.success(request, 'Режим уведомлений сохранён')
            elif action == 'add_date':
                date = notification_service.parse_iso_date(request.POST.get('date'))
                if subscription is None:  # первое действие — сразу режим конкретных дат
                    subscription = NotificationSubscription(
                        user=request.user, teacher=teacher, auditorium=auditorium,
                        mode=NotificationSubscription.Mode.DATES)
                dates = notification_service.parse_dates(subscription)
                if date in dates:
                    raise ValueError('Эта дата уже добавлена')
                dates.append(date)
                _save_dates(subscription, dates)
                # добавление даты означает выбор режима дат — иначе уведомления не появятся
                subscription.mode = NotificationSubscription.Mode.DATES
                subscription.save()
                messages.success(request, f'Дата {date.strftime("%d.%m.%Y")} добавлена '
                                          f'(режим: конкретные даты)')
            elif action == 'remove_date':
                date = notification_service.parse_iso_date(request.POST.get('date'))
                if subscription:
                    dates = notification_service.parse_dates(subscription)
                    if date in dates:
                        dates.remove(date)
                        _save_dates(subscription, dates)
                        subscription.save()
                        messages.success(request, 'Дата удалена')
            elif action == 'save_weekdays':
                week_days = [value for value in request.POST.getlist('week_day')
                             if notification_service.is_valid_week_day(value)]
                if subscription is None:  # первое действие — сразу режим дней недели
                    subscription = NotificationSubscription(
                        user=request.user, teacher=teacher, auditorium=auditorium,
                        mode=NotificationSubscription.Mode.WEEKDAYS)
                _save_week_days(subscription, week_days)
                # сохранение дней означает выбор этого режима — иначе уведомления не появятся
                subscription.mode = NotificationSubscription.Mode.WEEKDAYS
                subscription.save()
                messages.success(request, 'Дни недели сохранены (режим: дни недели)')
        except Exception as e:
            for error in get_error_messages(e):
                messages.error(request, error)
        url_name = 'notification_teacher_settings' if teacher else 'notification_auditorium_settings'
        object_id = teacher.pk if teacher else auditorium.pk
        return redirect(reverse(url_name, args=[object_id]))

    dates = notification_service.parse_dates(subscription) if subscription else []
    checked_week_days = set(json.loads(subscription.week_days or '[]')) if subscription else set()
    # готовая структура для шаблона: в Django-шаблонах нет проверки вхождения в список
    week_rows = [{'number': week_number,
                  'days': [{'key': day_key, 'label': day_label,
                            'checked': f'{week_number}-{day_key}' in checked_week_days}
                           for day_key, day_label in LessonForm().week_day]}
                 for week_number in (1, 2)]
    data = {
        'subject_kind': 'teacher' if teacher else 'auditorium',
        'subject_title': f'преподаватель {teacher.name}'
        + (f', {teacher.title}' if teacher and teacher.title else '')
        if teacher else
        f'аудитория {auditorium.number}'
        + (f' (корпус {auditorium.building})' if auditorium.building else ''),
        'subject_id': teacher.pk if teacher else auditorium.pk,
        'subscription': subscription,
        'mode': subscription.mode if subscription else None,
        'dates': dates,
        'week_rows': week_rows,
        'week_days': LessonForm().week_day,
        'modes': NotificationSubscription.Mode,
    }
    return render(request, 'main/notifications/NotificationSettingsPage.html', context=data)


@login_required
def notifications_data(request):
    """JSON для шторки уведомлений: {count, groups}."""
    return JsonResponse(notification_service.collect_notifications(request.user))

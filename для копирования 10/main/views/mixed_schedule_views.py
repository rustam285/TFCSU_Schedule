import copy
import datetime
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from ..forms import LessonForm
from ..models import Lesson, TemporarySchedule
from ..backup import create_backup
from ..services import (discipline_service, lesson_service, util, group_service,
                        auditorium_service, teacher_service)
from ..services.mixed_schedule_service import delete_mixed_schedule_by_date_interval
from ..services.temporary_schedule_service import delete_lessons_by_date, get_query_for_table_by_date, update, \
    get_by_group_and_date, get_by_pk
from ..services.util import get_week_number, get_weekday_by_date, convert_string_to_date, get_data_for_schedule, \
    get_dates, get_error_messages, normalize_import_auditorium
from ..services.validation_service import validate_input_dates_correct, validate_import_group_title, \
    validate_import_input_values


@login_required
def render_add_page(request):
    if request.method == "GET":
        mixed_groups = group_service.get_by_form_of_education('о-з')
        default_group = mixed_groups.order_by('id').first()
        chosen_group_id = request.GET.get('chosen_group', default_group.id if default_group else None)
        data = {
            'numbers': LessonForm().NUMBER_OF_LESSON_CHOICES.items(),
            'week_numbers': LessonForm().week_number,
            'disciplines': discipline_service.get_all(),
            'teachers': teacher_service.get_all(),
            'auditoriums': auditorium_service.get_all(),
            'groups': mixed_groups,
            'chosen_group': group_service.get_by_pk(chosen_group_id) if chosen_group_id else None,
            'chosen_date': request.GET.get('chosen_date', util.get_today_date()),
            'chosen_week_number': request.GET.get('chosen_week_number', '1'),
        }
        if not default_group:
            messages.error(request, "В базе нет групп очно-заочной формы обучения")
        elif data['chosen_group'] and data['chosen_date'] != '':
            data['mixed_query'] = get_query_for_table_by_date(
                data['chosen_group'],
                data['chosen_date'],
            )
        return render(request, "main/MixedAddSchedule.html", context=data)
    if request.method == "POST":
        needed_group = request.POST.get('selected_group')
        needed_date = request.POST.get('selected_date')
        needed_week = request.POST.get('selected_week_number')
        if needed_date == '':
            messages.error(request, "Дата не выбрана")
        else:
            try:
                number = float(request.POST.get('selected_number').replace(",", "."))
            except (TypeError, ValueError):
                number = None
            if number is None:
                messages.error(request, "Некорректный номер занятия")
            else:
                new_lesson = Lesson(
                    number=number,
                    is_special=bool(request.POST.get('is_special')),
                    discipline=discipline_service.get_by_pk(request.POST.get('selected_discipline')),
                    format=request.POST.get('format') or '',
                    teacher=teacher_service.get_by_pk(request.POST.get('selected_teacher')),
                    auditorium=auditorium_service.get_by_pk(request.POST.get('selected_auditorium')),
                    group=group_service.get_by_pk(needed_group),
                )
                new_slot = TemporarySchedule(lesson=new_lesson, date=needed_date)
                lesson_service.update(new_lesson)
                update(new_slot)
        base_url = reverse('add_mixed_schedule')
        url = f'{base_url}?chosen_group={needed_group}&chosen_date={needed_date}&chosen_week_number={needed_week}'
        if request.POST.get('return_to_main'):
            base_url = reverse('check_schedule_group')
            chosen_date_start = request.POST.get('chosen_date_start')
            chosen_date_end = request.POST.get('chosen_date_end')
            url = f'{base_url}?chosen_group={needed_group}&chosen_date_start={chosen_date_start}&chosen_date_end={chosen_date_end}'
        return redirect(url)


@login_required
def render_edit_page(request):
    if request.method == "GET":
        time = LessonForm().time
        mixed_groups = group_service.get_by_form_of_education('о-з')
        default_group = mixed_groups.order_by('id').first()
        chosen_group_id = request.GET.get('chosen_group', default_group.id if default_group else None)
        data = {
            'groups': mixed_groups,
            'chosen_group': group_service.get_by_pk(chosen_group_id) if chosen_group_id else None,
            'chosen_date': request.GET.get('chosen_date', util.get_today_date()),
        }
        if not default_group:
            messages.error(request, "В базе нет групп очно-заочной формы обучения")
        elif data['chosen_group'] and data['chosen_date']:
            chosen_date_label = util.reformat_date_string(data['chosen_date']) + ', ' + LessonForm().week_day[
                get_weekday_by_date(convert_string_to_date(data['chosen_date']))][1]
            data['chosen_date_label'] = chosen_date_label
            data['week_number'] = get_week_number(convert_string_to_date(data['chosen_date']))
            query = get_by_group_and_date(data['chosen_group'], data['chosen_date'])
            for i in query:
                i.time = time[i.lesson.number]
            data['query'] = query

        return render(request, 'main/MixedEditSchedule.html', context=data)


@login_required
def render_edit_page_for_chosen_lesson(request, slot_id):
    time = LessonForm().time
    slot = get_by_pk(slot_id)
    chosen_date_start = request.GET.get('chosen_date_start')
    chosen_date_end = request.GET.get('chosen_date_end')
    # Подгрузка всех возможных вариантов для изменения
    if request.method == "GET":
        data = {
            'slot': slot,
            'time': time[slot.lesson.number],
            "numbers": LessonForm().NUMBER_OF_LESSON_CHOICES.items(),
            "week_numbers": LessonForm().week_number,
            "auditoriums": auditorium_service.get_all(),
            "teachers": teacher_service.get_all(),
            'disciplines': discipline_service.get_all(),
            'chosen_date': str(slot.date),
        }
        if request.GET.get('chosen_date_start') and request.GET.get('chosen_date_end'):
            data['chosen_date_start'] = request.GET.get('chosen_date_start')
            data['chosen_date_end'] = request.GET.get('chosen_date_end')
        else:
            data['chosen_date_start'] = datetime.date.today().strftime('%Y-%m-%d')
            data['chosen_date_end'] = str(slot.date)
        return render(request, 'main/MixedEditLesson.html', context=data)
    # Изменение данных выбранного занятия
    if request.method == "POST":
        updated_slot = copy.deepcopy(slot)
        updated_slot.date = request.POST.get('new_date')
        updated_slot.lesson.number = float(request.POST.get('new_number').replace(",", "."))
        updated_slot.lesson.is_special = bool(request.POST.get('is_special'))
        updated_slot.lesson.discipline = discipline_service.get_by_pk(request.POST.get('new_discipline'))
        updated_slot.lesson.format = request.POST.get('new_format') or ''
        updated_slot.lesson.teacher = teacher_service.get_by_pk(request.POST.get('new_teacher'))
        updated_slot.lesson.auditorium = auditorium_service.get_by_pk(request.POST.get('new_auditorium'))
        try:
            lesson_service.update(updated_slot.lesson)
            update(updated_slot)
        except Exception as e:
            for error in get_error_messages(e):
                messages.error(request, error)
        base_url = reverse('edit_mixed_lesson', kwargs={'slot_id': slot_id})

        url = f'{base_url}?chosen_date_start={chosen_date_start}&chosen_date_end={chosen_date_end}'
        return redirect(url)


MIXED_IMPORT_NUMBERS = {1.0, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0}


@csrf_exempt
@login_required
def render_import_page(request):
    """Страница мультифайлового импорта расписания очно-заочной формы."""
    if request.method == 'GET':
        data = get_data_for_schedule()
        data['numbers'] = range(1, 9)
        return render(request, 'main/schedule_import/ScheduleMixedImportPage.html', context=data)
    return HttpResponseNotAllowed(['GET'])


@csrf_exempt
@login_required
def save_imported_mixed_schedules(request):
    """Сохранение результатов мультифайлового импорта очно-заочного расписания (JSON).

    Запрос: {"entries": [{"groups": ["ТФИ-301"], "date_start": "ГГГГ-ММ-ДД",
        "date_end": "ГГГГ-ММ-ДД", "cells": {"<неделя>_<день>_<№ пары>":
        {is_special, discipline, format, teacher, auditorium}, ...}}, ...]}

    Файлы очно-заочной формы содержат недельную сетку на 2 недели (как очные),
    дат в них нет — интервал дат задаётся на странице. Пары сетки
    «разворачиваются» на каждую подходящую дату интервала (чётность недели +
    день недели) и сохраняются как TemporarySchedule. Старое расписание групп
    удаляется только внутри интервала записи. Записи валидируются независимо:
    сохраняются только безошибочные; ошибки — с ключом "_group" или ячейки.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Ожидается POST-запрос'}, status=405)
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Некорректный JSON в запросе'}, status=400)
    entries = payload.get('entries')
    if not isinstance(entries, list) or not entries:
        return JsonResponse({'error': 'Нет записей для сохранения'}, status=400)

    data = get_data_for_schedule()
    day_labels = dict(data['week_days'])  # 'пн' -> 'Понедельник'
    week_numbers = set(data['week_numbers'])  # {'1', '2'}

    results = []
    to_save = []
    for index, entry in enumerate(entries):
        groups = entry.get('groups')
        if isinstance(groups, str):
            groups = [part.strip() for part in groups.split(',')]
        elif isinstance(groups, list):
            groups = [str(part).strip() for part in groups]
        else:
            groups = []
        # уникальные названия с сохранением порядка
        groups = list(dict.fromkeys(g for g in groups if g))

        errors = {}
        valid_groups = []
        for group_title in groups:
            try:
                validate_import_group_title(group_title)
            except Exception as e:
                errors.setdefault('_group', []).extend(get_error_messages(e))
                continue
            if group_service.get_by_title(group_title).form_of_education != 'о-з':
                errors.setdefault('_group', []).append(
                    f'Группа не относится к очно-заочной форме обучения: {group_title}')
            else:
                valid_groups.append(group_title)

        date_start = str(entry.get('date_start') or '').strip()
        date_end = str(entry.get('date_end') or '').strip()
        start = end = None
        if not date_start or not date_end:
            errors.setdefault('_group', []).append('Не задан интервал дат — укажите обе даты (с и по)')
        else:
            try:
                validate_input_dates_correct(date_start, date_end)
                start = convert_string_to_date(date_start)
                end = convert_string_to_date(date_end)
            except Exception as e:
                errors.setdefault('_group', []).extend(get_error_messages(e))

        prepared = []
        for key, cell in (entry.get('cells') or {}).items():
            parts = str(key).split('_')
            if len(parts) != 3 or parts[0] not in week_numbers or parts[1] not in day_labels:
                continue
            week, day_code, number_str = parts
            try:
                number = float(number_str.replace(',', '.'))
            except ValueError:
                continue
            if number not in MIXED_IMPORT_NUMBERS:
                continue
            discipline = str(cell.get('discipline') or '').strip()
            teacher = str(cell.get('teacher') or '').strip()
            fmt = str(cell.get('format') or '').strip()
            auditorium = normalize_import_auditorium(cell.get('auditorium'))
            if not (discipline or teacher or fmt or auditorium):
                continue
            try:
                validate_import_input_values(', '.join(groups), week, day_labels[day_code],
                                              number_str.replace('.0', ''), discipline,
                                              teacher, auditorium)
                prepared.append({'number': number,
                                 'is_special': bool(cell.get('is_special')),
                                 'discipline': discipline, 'format': fmt,
                                 'teacher': teacher, 'auditorium': auditorium,
                                 'week_day': day_code, 'week_number': int(week)})
            except Exception as e:
                errors.setdefault(str(key), []).extend(get_error_messages(e))

        if valid_groups and start and end and not errors and not prepared:
            errors.setdefault('_group', []).append('В файле не найдено ни одной пары — сохранять нечего')

        result = {'index': index, 'groups': groups, 'errors': errors}
        if errors or not valid_groups or start is None:
            result['status'] = 'failed'
        else:
            result['status'] = 'saved'
            to_save.append({'groups': valid_groups, 'prepared': prepared,
                            'start': start, 'end': end})
        results.append(result)

    if to_save:
        # страховочная копия базы перед перезаписью расписаний групп
        create_backup(reason='import')
    for item in to_save:
        # одна запись = одна колонка файла: все её группы делят общую сетку;
        # перезапись — только внутри интервала записи
        with transaction.atomic():
            for group_title in item['groups']:
                delete_mixed_schedule_by_date_interval(group_title, item['start'], item['end'])
            by_slot = {}
            for cell in item['prepared']:
                by_slot.setdefault((cell['week_number'], cell['week_day']), []).append(cell)
            for i_date in get_dates(item['start'], item['end']):
                week = get_week_number(i_date)
                day = data['week_days'][get_weekday_by_date(i_date)][0]
                for cell in by_slot.get((week, day), []):
                    for group_title in item['groups']:
                        new_lesson = Lesson(
                            number=cell['number'],
                            is_special=cell['is_special'],
                            discipline=discipline_service.get_by_title(cell['discipline']),
                            format=cell['format'],
                            teacher=teacher_service.get_by_name(cell['teacher']),
                            auditorium=auditorium_service.get_by_number(cell['auditorium']),
                            group=group_service.get_by_title(group_title),
                        )
                        lesson_service.update(new_lesson)
                        update(TemporarySchedule(lesson=new_lesson, date=i_date))

    return JsonResponse({'results': results})


@login_required
def render_delete_page(request):
    time = LessonForm().time
    if request.method == "GET":
        mixed_groups = group_service.get_by_form_of_education('о-з')
        default_group = mixed_groups.order_by('id').first()
        chosen_group_id = request.GET.get('chosen_group', default_group.id if default_group else None)
        chosen_date = request.GET.get('chosen_date', util.get_today_date())
        data = {
            'groups': mixed_groups,
            'chosen_group': chosen_group_id,
            'chosen_date': chosen_date,
        }
        if not default_group:
            messages.error(request, "В базе нет групп очно-заочной формы обучения")
        elif chosen_date == '':
            messages.error(request, "Дата не выбрана")
        elif chosen_group_id:
            schedule_by_date = get_by_group_and_date(group_service.get_by_pk(chosen_group_id),
                                                     chosen_date)
            for slot in schedule_by_date:
                slot.weekday = LessonForm().week_day[get_weekday_by_date(slot.date)][1]
                slot.week_number = get_week_number(slot.date)
                slot.lesson.time = time[slot.lesson.number]
            data['schedule_by_date'] = schedule_by_date
        return render(request, 'main/MixedDeleteSchedule.html', context=data)

    if request.method == "POST":
        chosen_group = request.POST.get('chosen_group')
        chosen_date = request.POST.get('chosen_date')
        if request.POST.get("deleting_lesson_id"):  # выбранный урок
            lesson_service.delete_by_pk(int(request.POST.get('deleting_lesson_id')))
        elif request.POST.get("deleting_group_id"):  # всё расписание для определённой группы
            Lesson.objects.filter(group=request.POST.get('chosen_group')).delete()
        elif request.POST.get("deleting_date_id"):  # всё расписание для определённой даты
            delete_lessons_by_date(request.POST.get("deleting_date_id"))
        base_url = reverse('delete_mixed_schedule')
        url = f'{base_url}?chosen_group={chosen_group}&chosen_date={chosen_date}'
        if request.POST.get('return_to_main'):
            chosen_date_start = request.POST.get('chosen_date_start')
            chosen_date_end = request.POST.get('chosen_date_end')
            base_url = reverse('check_schedule_group')
            url = f'{base_url}?chosen_group={chosen_group}&chosen_date_start={chosen_date_start}&chosen_date_end={chosen_date_end}'
        return redirect(url)

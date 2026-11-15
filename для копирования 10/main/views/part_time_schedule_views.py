import copy
import json
from datetime import datetime

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
from ..services import (group_service, discipline_service, lesson_service,
                        auditorium_service, teacher_service, util)
from ..services.temporary_schedule_service import delete_lessons_by_date, get_by_group_and_date, update, get_by_pk, \
    get_by_group
from ..services.util import convert_schedule_string_to_date, get_data_for_schedule, convert_date_to_string, \
    get_error_messages, normalize_import_auditorium
from ..services.validation_service import validate_import_group_title, validate_import_input_values_for_date


@login_required
def render_add_page(request):
    time = LessonForm().time
    if request.method == "GET":
        part_time_groups = group_service.get_by_form_of_education('з')
        default_group = part_time_groups.order_by('id').first()
        chosen_group_id = request.GET.get('chosen_group', default_group.id if default_group else None)
        data = {
            'numbers': LessonForm().NUMBER_OF_LESSON_CHOICES.items(),
            'time': time,
            'disciplines': discipline_service.get_all(),
            'teachers': teacher_service.get_all(),
            'auditoriums': auditorium_service.get_all(),
            'groups': part_time_groups,
            'chosen_group': group_service.get_by_pk(chosen_group_id) if chosen_group_id else None,
            'chosen_date': request.GET.get('chosen_date', datetime.now().strftime("%Y-%m-%d")),
        }
        if not default_group:
            messages.error(request, "В базе нет групп заочной формы обучения")
        elif data['chosen_group'] and data['chosen_date']:
            data['chosen_date_label'] = util.reformat_date_string(data['chosen_date'])
            schedule_by_date = get_by_group_and_date(data['chosen_group'], data['chosen_date'])
            for i in schedule_by_date:
                i.time = time[i.lesson.number]
            data['schedule_by_date'] = schedule_by_date
        return render(request, "main/PartTimeAddSchedule.html", context=data)
    if request.method == "POST":
        needed_group = request.POST.get('selected_group')
        needed_date = request.POST.get('selected_date')
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
        base_url = reverse('add_part_time_schedule')
        url = f'{base_url}?chosen_group={needed_group}&chosen_date={needed_date}'
        if request.POST.get('return_to_main'):
            base_url = reverse('check_schedule_group')
            chosen_date_start = request.POST.get('chosen_date_start')
            chosen_date_end = request.POST.get('chosen_date_end')
            url = (f'{base_url}?chosen_group={needed_group}&'
                   f'chosen_date_start={chosen_date_start}&'
                   f'chosen_date_end={chosen_date_end}')
        return redirect(url)


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
            'lesson_number': LessonForm().NUMBER_OF_LESSON_CHOICES[slot.lesson.number],
            'time': time[slot.lesson.number],
            "numbers": LessonForm().NUMBER_OF_LESSON_CHOICES.items(),
            "auditoriums": auditorium_service.get_all(),
            "teachers": teacher_service.get_all(),
            'disciplines': discipline_service.get_all(),
            'chosen_date_to_param': convert_date_to_string(slot.date),
            'chosen_group': slot.lesson.group.id,
            'chosen_date': str(slot.date),
        }
        if request.GET.get('chosen_date_start') and request.GET.get('chosen_date_end'):
            data['chosen_date_start'] = request.GET.get('chosen_date_start')
            data['chosen_date_end'] = request.GET.get('chosen_date_end')
        else:
            data['chosen_date_start'] = datetime.now().strftime('%Y-%m-%d')
            data['chosen_date_end'] = str(slot.date)
        return render(request, 'main/TempLessonEditPage.html', context=data)
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
        base_url = reverse('edit_part_time_lesson', kwargs={'slot_id': slot_id})

        url = f'{base_url}?chosen_date_start={chosen_date_start}&chosen_date_end={chosen_date_end}'
        return redirect(url)


PART_TIME_IMPORT_NUMBERS = set(range(1, 9))


@csrf_exempt
@login_required
def render_import_page(request):
    """Страница мультифайлового импорта расписания заочной формы обучения."""
    if request.method == "GET":
        data = get_data_for_schedule()
        data['numbers'] = range(1, 9)
        return render(request, 'main/schedule_import/SchedulePartTimeImportPage.html', context=data)
    return HttpResponseNotAllowed(['GET'])


@csrf_exempt
@login_required
def save_imported_part_time_schedules(request):
    """Сохранение результатов мультифайлового импорта заочного расписания (JSON).

    Запрос: {"entries": [{"groups": ["ТФИ-401"],
        "cells": {"<дата ДД.ММ.ГГГГ>_<№ пары>": {is_special, discipline, format,
        teacher, auditorium}, ...}}, ...]}

    Записи валидируются независимо друг от друга: сохраняются только записи
    без ошибок. Расписание групп записи полностью перезаписывается — все
    прежние пары группы удаляются, пары файла создаются как TemporarySchedule
    по своим датам. Ошибки возвращаются с ключом "_group" (уровень записи)
    или с ключом ячейки.
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
            if group_service.get_by_title(group_title).form_of_education != 'з':
                errors.setdefault('_group', []).append(
                    f'Группа не относится к заочной форме обучения: {group_title}')
            else:
                valid_groups.append(group_title)

        prepared = []
        for key, cell in (entry.get('cells') or {}).items():
            parts = str(key).split('_')
            if len(parts) != 2:
                continue
            date_str, number_str = parts
            try:
                date = convert_schedule_string_to_date(date_str)
                number = int(number_str)
            except ValueError:
                continue
            if number not in PART_TIME_IMPORT_NUMBERS:
                continue
            discipline = str(cell.get('discipline') or '').strip()
            teacher = str(cell.get('teacher') or '').strip()
            fmt = str(cell.get('format') or '').strip()
            auditorium = normalize_import_auditorium(cell.get('auditorium'))
            if not (discipline or teacher or fmt or auditorium):
                continue
            try:
                validate_import_input_values_for_date(', '.join(groups), date_str, number_str,
                                                       discipline, teacher, auditorium)
                prepared.append({'number': float(number),
                                 'is_special': bool(cell.get('is_special')),
                                 'discipline': discipline, 'format': fmt,
                                 'teacher': teacher, 'auditorium': auditorium,
                                 'date': date})
            except Exception as e:
                errors.setdefault(str(key), []).extend(get_error_messages(e))

        if valid_groups and not errors and not prepared:
            errors.setdefault('_group', []).append('В файле не найдено ни одной пары — сохранять нечего')

        result = {'index': index, 'groups': groups, 'errors': errors}
        if errors or not valid_groups:
            result['status'] = 'failed'
        else:
            result['status'] = 'saved'
            to_save.append({'groups': valid_groups, 'prepared': prepared})
        results.append(result)

    if to_save:
        # страховочная копия базы перед перезаписью расписаний групп
        create_backup(reason='import')
    for item in to_save:
        # одна запись = одна колонка файла: все её группы делят общие пары;
        # перезапись полная — прежнее расписание групп записи удаляется целиком
        with transaction.atomic():
            for group_title in item['groups']:
                Lesson.objects.filter(group=group_service.get_by_title(group_title)).delete()
            for cell in item['prepared']:
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
                    update(TemporarySchedule(lesson=new_lesson, date=cell['date']))

    return JsonResponse({'results': results})


@login_required
def render_edit_page(request):
    time = LessonForm().time
    if request.method == "GET":
        default_group = group_service.get_all().order_by('id').first()
        chosen_group = int(request.GET.get('chosen_group', default_group.id if default_group else -1))
        chosen_date = request.GET.get('chosen_date')
        data = {
            'groups': group_service.get_all(),
            'day': LessonForm().week_day,
            'weeks': LessonForm().week_number,
            'chosen_group': chosen_group,
            'chosen_date': chosen_date,
        }
        if chosen_date == '' or chosen_date == 'undefined' or chosen_date == 'None' or not chosen_date:
            schedule_by_date = get_by_group(chosen_group)
        else:
            schedule_by_date = get_by_group_and_date(group_service.get_by_pk(chosen_group),
                                                     chosen_date)
        for slot in schedule_by_date:
            slot.lesson.time = time[slot.lesson.number]
            slot.lesson.number = LessonForm().NUMBER_OF_LESSON_CHOICES[slot.lesson.number]
        data['schedule_by_date'] = schedule_by_date
        if request.GET.get('chosen_date_start'):
            data['chosen_date_start'] = request.GET.get('chosen_date_start')
            data['chosen_date_end'] = request.GET.get('chosen_date_end')
        return render(request, 'main/TempScheduleEditPage.html', context=data)
    if request.method == "POST":
        chosen_group = request.POST.get('chosen_group')
        chosen_date = request.POST.get('chosen_date')
        if request.POST.get("deleting_lesson_id"):  # выбранный урок
            lesson_service.delete_by_pk(int(request.POST.get('deleting_lesson_id')))
        elif request.POST.get("deleting_group_id"):  # всё расписание для определённой группы
            Lesson.objects.filter(group=request.POST.get('chosen_group')).delete()
        elif chosen_date == '':  # дата не выбрана
            messages.error(request, "Дата не выбрана")
        elif request.POST.get("deleting_date_id") and chosen_date != '':  # всё расписание для определённой даты
            delete_lessons_by_date(request.POST.get("deleting_date_id"))
        base_url = reverse('delete_part_time_schedule')
        url = f'{base_url}?chosen_group={chosen_group}&chosen_date={chosen_date}'
        return redirect(url)

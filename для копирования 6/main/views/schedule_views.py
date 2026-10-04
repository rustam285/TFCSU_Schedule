import copy
import json

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from ..forms import LessonForm
from ..models import Lesson, ConstantSchedule, TemporarySchedule
from ..backup import create_backup
from ..services import (group_service, discipline_service, lesson_service,
                        auditorium_service, teacher_service)
from ..services.constant_schedule_service import get_by_pk, update, get_query_for_table, \
    get_by_time, get_const_schedule_for_group_by_week_and_weekday, get_const_schedule_for_group
from ..services.temporary_schedule_service import get_query_for_table_by_date
from ..services.util import get_data_for_schedule, get_error_messages
from ..services.validation_service import validate_import_group_title, validate_import_input_values


@login_required
def render_edit_schedule_page(request):
    if request.method == "GET":
        time = LessonForm().time
        full_time_groups = group_service.get_by_form_of_education('о')
        if not full_time_groups.exists():
            messages.error(request, "В базе нет групп очной формы обучения")
            return render(request, 'main/ScheduleEditPage.html',
                          context={'groups': full_time_groups, 'days': LessonForm().week_day,
                                   'weeks': ["1", "2"]})
        data = {
            "number_of_lessons": LessonForm().NUMBER_OF_LESSON_CHOICES.items(),
            "time": time,
            'groups': full_time_groups,
            'days': LessonForm().week_day,
            'weeks': ["1", "2"],
            'chosen_group': group_service.get_by_pk(request.GET.get('chosen_group',
                                                                    full_time_groups.order_by('id').first().id)),
            'chosen_day': request.GET.get('chosen_day', 'пн'),
            'chosen_week': request.GET.get('chosen_week', '1')
        }
        lessons_for_group = get_const_schedule_for_group_by_week_and_weekday(
            group_id=data['chosen_group'].id,
            week=int(data['chosen_week']),
            weekday=data['chosen_day'])
        for i in lessons_for_group:
            i.time = time[i.lesson.number]
        data['lessons_for_group'] = lessons_for_group
        return render(request, 'main/ScheduleEditPage.html', context=data)


@login_required
def render_edit_schedule_page_for_chosen_lesson(request, slot_id):
    time = LessonForm().time
    slot = get_by_pk(slot_id)
    slot.week_day_label = dict(LessonForm().week_day).get(slot.week_day)
    # Подгрузка всех возможных вариантов для изменения
    if request.method == "GET":
        data = {
            'slot': slot,
            'lesson_number': LessonForm().NUMBER_OF_LESSON_CHOICES[slot.lesson.number],
            'time': time[slot.lesson.number],
            'week_numbers' : [1, 2],
            'week_days': LessonForm().week_day,
            "numbers": LessonForm().NUMBER_OF_LESSON_CHOICES.items(),
            "auditoriums": auditorium_service.get_all(),
            "teachers": teacher_service.get_all(),
            'disciplines': discipline_service.get_all(),
            'chosen_group': slot.lesson.group.id
        }
        return render(request, 'main/ConstLessonEditPage.html', context=data)
    # Изменение данных выбранного занятия
    if request.method == "POST":
        updated_slot = copy.deepcopy(slot)
        updated_slot.week_number = request.POST.get('new_week_number')
        updated_slot.week_day = request.POST.get('new_week_day')
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
        return redirect('for_edit_lesson', slot_id=slot_id)


@login_required
def render_add_schedule_page(request):
    time = LessonForm().time
    if request.method == "GET":
        all_groups = group_service.get_all()
        default_group_ids = [str(all_groups.first().id)] if all_groups else []
        data = {
            'numbers': LessonForm().NUMBER_OF_LESSON_CHOICES.items(),
            'time': time,
            'disciplines': discipline_service.get_all(),
            'teachers': teacher_service.get_all(),
            'auditoriums': auditorium_service.get_all(),
            'groups': all_groups,
            'week_days': LessonForm().week_day,
            'week_numbers': ["1", "2"],
            'chosen_groups': [group_service.get_by_pk(i) for i in
                              (request.GET.getlist('chosen_groups') or default_group_ids)],
            'chosen_day': request.GET.get('chosen_day', 'пн'),
            'chosen_week': request.GET.get('chosen_week', '1'),
            'chosen_date': request.GET.get('chosen_date'),
            'is_temp': request.GET.get('is_temp')
        }
        tables = []
        for group in data['chosen_groups']:
            if data['is_temp']=="on" and data['chosen_date'] and data['chosen_date']!="":
                query = get_query_for_table_by_date(group, data['chosen_date'])
            else:
                query = get_query_for_table(group, data['chosen_day'], data['chosen_week'])
            tables.append({'group': group,
                           'query': query})
        data['tables'] = tables
        return render(request, "main/ScheduleAddPage.html", context=data)
    if request.method == "POST":
        needed_groups = request.POST.getlist('selected_groups')
        needed_day = request.POST.get('selected_day')
        needed_week = request.POST.get('selected_week')
        needed_date = request.POST.get('selected_date')
        is_temp = request.POST.get('is_temp')
        if not needed_groups:
            messages.error(request, "Не выбрана ни одна группа")
            return redirect('schedule')
        try:
            number = float(request.POST.get('selected_number').replace(",", "."))
        except (TypeError, ValueError):
            messages.error(request, "Некорректный номер занятия")
            return redirect('schedule')
        for needed_group in needed_groups:
            new_lesson = Lesson(
                number=number,
                is_special=bool(request.POST.get('is_special')),
                discipline=discipline_service.get_by_pk(request.POST.get('selected_discipline')),
                format=request.POST.get('format') or '',
                teacher=teacher_service.get_by_pk(request.POST.get('selected_teacher')),
                auditorium=auditorium_service.get_by_pk(request.POST.get('selected_auditorium')),
                group=group_service.get_by_pk(needed_group),
            )
            try:
                if is_temp == "on":
                    new_slot = TemporarySchedule(lesson=new_lesson, date=needed_date)
                else:
                    new_slot = ConstantSchedule(lesson=new_lesson, week_day=needed_day,
                                                week_number=int(needed_week))
                lesson_service.update(new_lesson)
                update(new_slot)
            except Exception as e:
                for error in get_error_messages(e):
                    messages.error(request, error)

        base_url = reverse('schedule')
        url = f'{base_url}?'
        for group in needed_groups:
            url += f'chosen_groups={group}&'
        url += (f'chosen_day={needed_day}&chosen_week={needed_week}'
                f'&is_temp={is_temp}'
                f'{f'&chosen_date={needed_date}' if is_temp=="on" else ''}')
        if request.POST.get('return_to_main'):
            base_url = reverse('check_schedule_group')
            url = (f'{base_url}?chosen_group={needed_groups[0]}'
                   f'&chosen_day={needed_day}'
                   f'&chosen_week={needed_week}')
        return redirect(url)


@login_required
def render_delete_schedule_page(request):
    time = LessonForm().time
    if request.method == "GET":
        chosen_group = int(request.GET.get('chosen_group',
                                           group_service.get_by_form_of_education('о').order_by('id').first().id))
        schedule = get_const_schedule_for_group(group_id=chosen_group)
        for slot in schedule:
            slot.lesson.time = time[slot.lesson.number]
            slot.lesson.number = LessonForm().NUMBER_OF_LESSON_CHOICES[slot.lesson.number]

        data = {
            'groups': group_service.get_all(),
            'day': LessonForm().week_day,
            'weeks': ['1', '2'],
            'schedule_by_day': schedule,
            'chosen_group': chosen_group
        }
        return render(request, 'main/ConstScheduleEditPage.html', context=data)
    if request.method == "POST":
        chosen_group = request.POST.get('chosen_group')
        chosen_day = request.POST.get('chosen_day')
        chosen_week = request.POST.get('chosen_week')
        if request.POST.get("deleting_lesson_id"):  # выбранный урок
            lesson_service.delete_by_pk(int(request.POST.get('deleting_lesson_id')))
        elif request.POST.get("deleting_group_id"):  # всё расписание для определённой группы
            Lesson.objects.filter(group=chosen_group).delete()
        elif request.POST.get("deleting_week_id"):  # всё расписание для определённой группы и недели
            for i in get_by_time(needed_week=chosen_week).filter(lesson__group=chosen_group):
                lesson_service.delete_by_pk(i.lesson.pk)
        elif request.POST.get("deleting_day_id"):  # всё расписание для определённой группы, дня и недели
            for i in get_by_time(chosen_day, chosen_week).filter(lesson__group=chosen_group):
                lesson_service.delete_by_pk(i.lesson.pk)
        base_url = reverse('delete_schedule')
        if request.POST.get('return_to_main') == "True":
            base_url = reverse('check_schedule_group')
        url = f'{base_url}?chosen_group={chosen_group}&chosen_day={chosen_day}&chosen_week={chosen_week}'
        return redirect(url)


FULL_TIME_IMPORT_NUMBERS = {1.0, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0}


@csrf_exempt
@login_required
def render_import_schedule_page_vo(request):
    """Страница мультифайлового импорта очного расписания — файлы ВО."""
    return _render_import_page(request, 'higher_education', 'ВО')


@csrf_exempt
@login_required
def render_import_schedule_page_spo(request):
    """Страница мультифайлового импорта очного расписания — файлы СПО."""
    return _render_import_page(request, 'secondary_vocational_education', 'СПО')


def _render_import_page(request, education_type, education_type_label):
    if request.method == 'GET':
        data = get_data_for_schedule()
        data['numbers'] = range(1, 9)
        data['education_type'] = education_type
        data['education_type_label'] = education_type_label
        return render(request, 'main/schedule_import/ScheduleFullTimeImportPage.html', context=data)
    return HttpResponseNotAllowed(['GET'])


def _parse_import_auditorium(value):
    """Аудитория из JSON парсера: 214 (int) или 214.0 (float) -> '214'."""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value or '').strip()


@csrf_exempt
@login_required
def save_imported_full_time_schedules(request):
    """Сохранение результатов мультифайлового импорта очного расписания (JSON).

    Запрос: {"entries": [{"groups": ["ТСПД-201", "ТСПД-203"],
        "cells": {"<неделя>_<день>_<№ пары>": {is_special, discipline, format,
        teacher, auditorium}, ...}}, ...]}

    Записи валидируются независимо друг от друга: сохраняются только записи
    без ошибок (расписание каждой группы записи полностью перезаписывается),
    по ошибочным возвращаются ошибки уровня записи (ключ "_group") и
    отдельных ячеек (ключ ячейки).
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
                valid_groups.append(group_title)
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
            if number not in FULL_TIME_IMPORT_NUMBERS:
                continue
            discipline = str(cell.get('discipline') or '').strip()
            teacher = str(cell.get('teacher') or '').strip()
            fmt = str(cell.get('format') or '').strip()
            auditorium = _parse_import_auditorium(cell.get('auditorium'))
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
        # одна запись = одна колонка файла: все её группы делят общую сетку
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
                    update(ConstantSchedule(lesson=new_lesson, week_day=cell['week_day'],
                                            week_number=cell['week_number']))

    return JsonResponse({'results': results})

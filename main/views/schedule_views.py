import copy

from django.contrib.auth.decorators import login_required
from django.contrib import messages
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


@csrf_exempt
@login_required
def render_import_schedule_page(request):
    data = get_data_for_schedule()
    data["numbers"] = range(1, 9)
    if request.method == "GET":
        return render(request, 'main/schedule_import/ScheduleFullTimeImportPage.html', context=data)
    if request.method == "POST":
        schedule = []
        groups = request.POST.get('needed_groups').split(',')
        for group_title in groups:
            try:
                validate_import_group_title(group_title)
            except Exception as e:
                for error in get_error_messages(e):
                    messages.error(request, error)
                continue
            for week in data['week_numbers']:
                for day in data['week_days']:
                    for number in data['numbers']:
                        prefix = f'{week}_{day[0]}_{number}'
                        if (request.POST.get(f'{prefix}_discipline') == '' and
                                request.POST.get(f'{prefix}_teacher') == '' and
                                request.POST.get(f'{prefix}_format') == '' and
                                request.POST.get(f'{prefix}_auditorium') == ''):
                            continue
                        try:
                            validate_import_input_values(group_title, week, day[1], number,
                                                         request.POST.get(f'{prefix}_discipline'),
                                                         request.POST.get(f'{prefix}_teacher'),
                                                         request.POST.get(f'{prefix}_auditorium'))
                            new_lesson = Lesson(
                                number=number,
                                is_special=bool(request.POST.get(f'{prefix}_is_special')),
                                discipline=discipline_service.get_by_title(
                                    request.POST.get(f'{prefix}_discipline')),
                                format=request.POST.get(f'{prefix}_format') or '',
                                teacher=teacher_service.get_by_name(
                                    request.POST.get(f'{prefix}_teacher')),
                                auditorium=auditorium_service.get_by_number(
                                    request.POST.get(f'{prefix}_auditorium')),
                                group=group_service.get_by_title(group_title),
                            )
                            new_slot = ConstantSchedule(lesson=new_lesson, week_day=day[0], week_number=int(week))
                            schedule.append((new_lesson, new_slot))
                        except Exception as e:
                            for error in get_error_messages(e):
                                messages.error(request, error)
        if not messages.get_messages(request):
            # перед перезаписью расписания групп — страховочная копия базы
            create_backup(reason='import')
            for group_title in groups:
                Lesson.objects.filter(group=group_service.get_by_title(group_title)).delete()
            for lesson, slot in schedule:
                lesson_service.update(lesson)
                update(slot)
            messages.success(request, f'Расписание успешно загружено для групп: ' + ', '.join(groups))
    base_url = reverse('import_schedule')
    url = f'{base_url}'
    return redirect(url)

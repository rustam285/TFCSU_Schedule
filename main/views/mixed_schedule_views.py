import copy
import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
    get_error_messages
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


@csrf_exempt
@login_required
def render_import_page(request):
    data = get_data_for_schedule()
    data["numbers"] = range(1, 9)
    if request.method == "GET":
        return render(request, 'main/schedule_import/ScheduleMixedImportPage.html', context=data)
    if request.method == "POST":
        schedule = []
        start_date, end_date = request.POST.get('schedule_date_start'), request.POST.get('schedule_date_end')
        needed_group = request.POST.get('needed_group')
        try:
            validate_input_dates_correct(start_date, end_date)
            validate_import_group_title(needed_group)
        except Exception as e:
            for error in get_error_messages(e):
                messages.error(request, error)
        else:
            i_date = convert_string_to_date(start_date)
            while i_date != convert_string_to_date(end_date) + datetime.timedelta(days=1):
                week = get_week_number(i_date)
                day = data["week_days"][get_weekday_by_date(i_date)][0]
                for lesson_number in data["numbers"]:
                    prefix = f'{week}_{day}_{lesson_number}'
                    if (request.POST.get(f'{prefix}_discipline') == '' and
                            request.POST.get(f'{prefix}_teacher') == '' and
                            request.POST.get(f'{prefix}_format') == '' and
                            request.POST.get(f'{prefix}_auditorium') == ''):
                        continue
                    try:
                        validate_import_input_values(needed_group, week, day, lesson_number,
                                                     request.POST.get(f'{prefix}_discipline'),
                                                     request.POST.get(f'{prefix}_teacher'),
                                                     request.POST.get(f'{prefix}_auditorium'))
                        new_lesson = Lesson(
                            number=lesson_number,
                            is_special=bool(request.POST.get(f'{prefix}_is_special')),
                            discipline=discipline_service.get_by_title(
                                request.POST.get(f'{prefix}_discipline')),
                            format=request.POST.get(f'{prefix}_format') or '',
                            teacher=teacher_service.get_by_name(
                                request.POST.get(f'{prefix}_teacher')),
                            auditorium=auditorium_service.get_by_number(
                                request.POST.get(f'{prefix}_auditorium')),
                            group=group_service.get_by_title(needed_group),
                        )
                        new_slot = TemporarySchedule(lesson=new_lesson,
                                                     date=i_date)
                        schedule.append((new_lesson, new_slot))
                    except Exception as e:
                        for error in get_error_messages(e):
                            messages.error(request, error)
                i_date += datetime.timedelta(days=1)
        if not messages.get_messages(request):
            # перед перезаписью расписания группы — страховочная копия базы
            create_backup(reason='import')
            delete_mixed_schedule_by_date_interval(needed_group,
                                                   convert_string_to_date(start_date),
                                                   convert_string_to_date(end_date))
            for lesson, slot in schedule:
                lesson_service.update(lesson)
                update(slot)
            messages.success(request, f'Расписание успешно загружено для группы: ' + needed_group)
        base_url = reverse('import_mixed_schedule')
        return redirect(base_url)


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

import copy
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
    get_error_messages
from ..services.validation_service import validate_import_group_title, validate_imported_pt_lessons


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


def is_key_of_pt_lesson(key):
    try:
        date, number, name = key.split(sep="_")
        convert_schedule_string_to_date(date)
        number = int(number)
        if not number in range(1, 9): raise ValueError
        if not name in ['discipline', 'format', 'teacher', 'auditorium']: raise ValueError
    except ValueError:
        return False
    return True


def update_imported_pt_schedule(lessons, form_data):
    for date, lesson in lessons.items():
        for number, lesson_data in lesson.items():
            new_lesson = Lesson(
                number=float(number),
                is_special=lesson_data["is_special"],
                discipline=discipline_service.get_by_title(lesson_data["discipline"]),
                format=lesson_data["format"],
                teacher=teacher_service.get_by_name(lesson_data["teacher"]),
                auditorium=auditorium_service.get_by_number(lesson_data["auditorium"]),
                group=group_service.get_by_title(form_data["needed_group"])
            )
            new_slot = TemporarySchedule(lesson=new_lesson, date=convert_schedule_string_to_date(date))
            lesson_service.update(new_lesson)
            update(new_slot)


@csrf_exempt
@login_required
def render_import_page(request):
    data = get_data_for_schedule()
    if request.method == "GET":
        return render(request, 'main/schedule_import/SchedulePartTimeImportPage.html', context=data)
    if request.method == "POST":
        form_data = request.POST.dict()
        try:
            needed_group = request.POST.get('needed_group')
            validate_import_group_title(needed_group)
            lessons = {}
            for key, value in form_data.items():
                if is_key_of_pt_lesson(key):
                    date, number, name = key.split(sep="_")
                    if date not in lessons:
                        lessons[date] = {}
                    if number not in lessons[date]:
                        lessons[date][number] = {}
                    lessons[date][number][name] = value
                    if "is_special" not in lessons[date][number]:
                        lessons[date][number]["is_special"] = bool(request.POST.get(f'{date}_{number}_is_special'))
            validate_imported_pt_lessons(lessons)
            # перед перезаписью расписания группы — страховочная копия базы
            create_backup(reason='import')
            Lesson.objects.filter(group=group_service.get_by_title(needed_group)).delete()
            update_imported_pt_schedule(lessons, form_data)
            messages.success(request, f'Расписание успешно загружено для группы {needed_group}')
        except Exception as e:
            for error in get_error_messages(e):
                messages.error(request, error)
        base_url = reverse('import_part_time_schedule')
        url = f'{base_url}'
        return redirect(url)


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

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from main.constants import ptf_buttons, ftf_buttons, mf_buttons, admin_check_schedule_buttons, view_buttons
from main.forms import LessonForm
from main.models import Teacher, Auditorium
from main.services import group_service, validation_service, auditorium_service, teacher_service, discipline_service
from main.services.constant_schedule_service import get_query_for_table, get_table_query_for_teacher_by_dates, \
    get_table_query_for_auditorium_by_dates
from main.services.temporary_schedule_service import get_query_for_table_by_dates
from main.services.util import get_updated_at_from_json, update_updated_at_json, get_error_messages, get_today_date, \
    get_next_date, convert_string_to_date, get_dates


@login_required
def render_start_page(request):
    if request.method == 'GET':
        data = {
            'view_buttons': view_buttons,
            'ptf_buttons': ptf_buttons,
            'ftf_buttons': ftf_buttons,
            'mf_buttons': mf_buttons,
            'admin_check_schedule_buttons': admin_check_schedule_buttons,
            'updated_at': get_updated_at_from_json(),
            'groups_by_form': group_service.get_sorted_by_form_with_updated_at(),
        }
        return render(request, 'main/AdminHomePage.html', context=data)
    if request.method == 'POST':
        update_updated_at_json()
        return redirect('home')


@login_required
def render_schedule_by_group_page(request):
    data = return_fields_for_choice(request)
    if request.method == "GET":
        try:
            if data['chosen_date_start'] or data['chosen_date_end']:
                validation_service.validate_input_dates_correct(data['chosen_date_start'],
                                                                data['chosen_date_end'])
            chosen_group = group_service.get_by_pk(data['chosen_group']) \
                if data['chosen_group'] != -1 else None
            # пустой выбор дней/недель — понятная ошибка, а не «молчаливый» пн/1-я неделя
            if chosen_group is not None and chosen_group.form_of_education == 'о' \
                    and data['form_submitted'] \
                    and (not data['chosen_days'] or not data['chosen_weeks']):
                if not data['chosen_days']:
                    messages.error(request, 'Не выбран ни один день — отметьте нужные дни или «Все дни»')
                if not data['chosen_weeks']:
                    messages.error(request, 'Не выбрана ни одна неделя — отметьте недели или «Все недели»')
            else:
                add_table_data(data)
        except Exception as e:
            for error in get_error_messages(e):
                messages.error(request, error)

        return render(request, 'main/View_Schedule_By_Group.html', context=data)


@login_required
def check_schedule_teachers(request):
    data = {
        'teachers': teacher_service.get_all(),
        'auditoriums': auditorium_service.get_all(),
        'chosen_date_start': request.GET.get('chosen_date_start', get_today_date()),
        'chosen_date_end': request.GET.get('chosen_date_end', get_next_date()),
    }
    chosen_teacher_id = request.GET.get('chosen_teacher')
    if chosen_teacher_id:
        try:
            data['chosen_teacher'] = teacher_service.get_by_pk(chosen_teacher_id)
        except Teacher.DoesNotExist:
            messages.error(request, "Выбранный преподаватель не найден")
            data['chosen_teacher'] = None
    elif data['teachers']:
        data['chosen_teacher'] = data['teachers'].first()
    else:
        data['chosen_teacher'] = None
        messages.error(request, "В базе нет ни одного преподавателя")

    if data['chosen_teacher'] and request.method == "GET":
        try:
            validation_service.validate_input_dates_presented_and_correct(
                data['chosen_date_start'], data['chosen_date_end'])
            dates = get_dates_for_table_query(data['chosen_date_start'], data['chosen_date_end'])
            data['table_query'] = get_table_query_for_teacher_by_dates(
                data['chosen_teacher'], dates,
                viewer_is_authenticated=request.user.is_authenticated)
        except Exception as e:
            for error in get_error_messages(e):
                messages.error(request, error)
    return render(request, 'main/Check_Preps.html', context=data)


@login_required
def check_schedule_auditoriums(request):
    data = {
        'teachers': teacher_service.get_all(),
        'auditoriums': auditorium_service.get_all(),
        'chosen_date_start': request.GET.get('chosen_date_start', get_today_date()),
        'chosen_date_end': request.GET.get('chosen_date_end', get_next_date()),
    }
    chosen_auditorium_id = request.GET.get('chosen_auditorium')
    if chosen_auditorium_id:
        try:
            data['chosen_auditorium'] = auditorium_service.get_by_pk(chosen_auditorium_id)
        except Auditorium.DoesNotExist:
            messages.error(request, "Выбранная аудитория не найдена")
            data['chosen_auditorium'] = None
    elif data['auditoriums']:
        data['chosen_auditorium'] = data['auditoriums'].first()
    else:
        data['chosen_auditorium'] = None
        messages.error(request, "В базе нет ни одной аудитории")

    if data['chosen_auditorium'] and request.method == "GET":
        try:
            validation_service.validate_input_dates_presented_and_correct(
                data['chosen_date_start'], data['chosen_date_end'])
            dates = get_dates_for_table_query(data['chosen_date_start'], data['chosen_date_end'])
            data['table_query'] = get_table_query_for_auditorium_by_dates(data['chosen_auditorium'], dates)
        except Exception as e:
            for error in get_error_messages(e):
                messages.error(request, error)
    return render(request, 'main/Check_Aud.html', context=data)


def get_dates_for_table_query(start_date, end_date):
    if end_date == '':
        return [convert_string_to_date(start_date)]
    elif start_date == '':
        return [convert_string_to_date(end_date)]
    else:
        return get_dates(convert_string_to_date(start_date),
                         convert_string_to_date(end_date))


def return_fields_for_choice(request):
    add_lesson_data = {
        "numbers": LessonForm().NUMBER_OF_LESSON_CHOICES.items(),
        "auditoriums": auditorium_service.get_all(),
        "teachers": teacher_service.get_all(),
        'disciplines': discipline_service.get_all(),
    }
    week_day_keys = [day_key for day_key, _ in LessonForm().week_day]
    # «Все дни»/«Все недели» — отдельные чекбоксы; на свежей странице они отмечены
    if request.GET.get('all_days') == '1':
        chosen_days, all_days = week_day_keys, True
    elif 'chosen_day' in request.GET:
        chosen_days = [day for day in request.GET.getlist('chosen_day')
                       if day in week_day_keys]
        all_days = False
    elif 'form_submitted' in request.GET:
        chosen_days, all_days = [], False
    else:
        chosen_days, all_days = week_day_keys, True
    if request.GET.get('all_weeks') == '1':
        chosen_weeks, all_weeks = ['1', '2'], True
    elif 'chosen_week' in request.GET:
        chosen_weeks = [week for week in request.GET.getlist('chosen_week')
                        if week in ('1', '2')]
        all_weeks = False
    elif 'form_submitted' in request.GET:
        chosen_weeks, all_weeks = [], False
    else:
        chosen_weeks, all_weeks = ['1', '2'], True
    data = {
        'groups': group_service.get_all(),
        'days': LessonForm().week_day,
        'weeks': ["1", "2"],
        'add_lesson_data': add_lesson_data,
        'form_submitted': 'form_submitted' in request.GET,
        'all_days': all_days,
        'all_weeks': all_weeks,
        'chosen_days': chosen_days,
        'chosen_weeks': chosen_weeks,
        'chosen_day': chosen_days[0] if chosen_days else 'пн',   # для формы добавления занятия
        'chosen_week': chosen_weeks[0] if chosen_weeks else '1',
        'chosen_date_start': request.GET.get('chosen_date_start'),
        'chosen_date_end': request.GET.get('chosen_date_end'),
        'chosen_group': int(request.GET.get('chosen_group') if request.GET.get('chosen_group') else -1),
    }
    return data


def add_table_data(data):
    chosen_group_id = data['chosen_group']
    if chosen_group_id == -1:
        return
    chosen_group = group_service.get_by_pk(chosen_group_id)
    query = None
    match chosen_group.form_of_education:
        case "о":
            query = get_query_for_table(chosen_group, ' '.join(data['chosen_days']),
                                        ' '.join(data['chosen_weeks']))
        case "з":
            query = get_query_for_table_by_dates(chosen_group,
                                                 data['chosen_date_start'] or get_today_date(),
                                                 data['chosen_date_end'] or get_next_date())
        case "о-з":
            query = get_query_for_table_by_dates(chosen_group,
                                                 data['chosen_date_start'] or get_today_date(),
                                                 data['chosen_date_end'] or get_next_date())
    data['query'] = query
    data['group'] = chosen_group

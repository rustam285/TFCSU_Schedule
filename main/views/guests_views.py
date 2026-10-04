from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render

from main.services import util, group_service, teacher_service, auditorium_service
from main.services.constant_schedule_service import get_table_query_for_teacher_by_dates, \
    get_table_query_for_group_by_dates, get_table_query_for_auditorium_by_dates
from main.services.util import get_updated_at_from_json, get_dates, \
    convert_string_to_date, get_error_messages
from main.services.validation_service import validate_input_dates_presented_and_correct


def render_start_page(request):
    data = {
        'updated_at': get_updated_at_from_json()
    }
    return render(request, 'main/guest/GuestHomePage.html', context=data)


def get_dates_for_table_query(start_date, end_date):
    if end_date == '':
        return [convert_string_to_date(start_date)]
    elif start_date == '':
        return [convert_string_to_date(end_date)]
    else:
        return get_dates(convert_string_to_date(start_date),
                         convert_string_to_date(end_date))


def _get_or_default(get_pk_func, pk, all_objects, label):
    """Возвращает объект по pk (или первый из всех). При ошибке — None и текст ошибки."""
    if pk:
        try:
            return get_pk_func(pk), None
        except ObjectDoesNotExist:
            return None, f"Выбранный(-ая) {label} не найден(а)"
    first = all_objects.first()
    if not first:
        return None, f"В базе нет данных: {label}"
    return first, None


def render_schedule_by_group_page(request):
    if request.method == "GET":
        data = util.get_data_for_schedule()  # main info for render same pages
        # Проверяем какую именно форму использовали, чтобы при рендере отображать только ее
        data['is_full_time'] = request.GET.get('is_full_time')
        data['is_part_time'] = request.GET.get('is_part_time')
        data['is_mixed'] = request.GET.get('is_mixed')

        errors = []
        # Получаем данные формы по группам каждой формы обучения
        data['chosen_full_time_group'], error = _get_or_default(
            group_service.get_by_pk,
            request.GET.get('chosen_full_time_group'),
            data['full_time_groups'],
            "группа очной формы обучения")
        if error:
            errors.append(error)

        data['chosen_mixed_group'], error = _get_or_default(
            group_service.get_by_pk,
            request.GET.get('chosen_mixed_group'),
            data['mixed_groups'],
            "группа очно-заочной формы обучения")
        if error:
            errors.append(error)

        data['chosen_part_time_group'], error = _get_or_default(
            group_service.get_by_pk,
            request.GET.get('chosen_part_time_group'),
            data['part_time_groups'],
            "группа заочной формы обучения")
        if error:
            errors.append(error)

        data['chosen_date_start'] = request.GET.get('chosen_date_start', util.get_today_date())
        data['chosen_date_end'] = request.GET.get('chosen_date_end', util.get_next_date())
        # Проверяем по полученным данным формы, какой запрос нам необходимо выполнить
        try:
            validate_input_dates_presented_and_correct(data['chosen_date_start'], data['chosen_date_end'])
            dates = get_dates_for_table_query(data['chosen_date_start'], data['chosen_date_end'])

            if data['is_full_time'] and data['chosen_full_time_group']:
                data['full_time_table_query'] = get_table_query_for_group_by_dates(
                    data['chosen_full_time_group'],
                    dates)
            if data['is_mixed'] and data['chosen_mixed_group']:
                data['mixed_query'] = get_table_query_for_group_by_dates(
                    data['chosen_mixed_group'],
                    dates)
            if data['is_part_time'] and data['chosen_part_time_group']:
                data['part_time_query'] = get_table_query_for_group_by_dates(
                    data['chosen_part_time_group'],
                    dates)
        except Exception as e:
            errors.extend(get_error_messages(e))
        for error in errors:
            messages.error(request, error)
        return render(request, 'main/guest/GuestViewScheduleByGroupPage.html', context=data)


def render_schedule_by_teacher_page(request):
    if request.method == "GET":
        data = util.get_data_for_schedule()
        data['chosen_teacher'], error = _get_or_default(
            teacher_service.get_by_pk,
            request.GET.get('chosen_teacher'),
            data['teachers'],
            "преподаватель")
        if error:
            messages.error(request, error)
        # Получаем временные данные
        data['chosen_date_start'] = request.GET.get('chosen_date_start', util.get_today_date())
        data['chosen_date_end'] = request.GET.get('chosen_date_end', util.get_next_date())
        # Проверяем по полученным данным формы, какой запрос нам необходимо выполнить
        try:
            validate_input_dates_presented_and_correct(data['chosen_date_start'], data['chosen_date_end'])
            dates = get_dates_for_table_query(data['chosen_date_start'], data['chosen_date_end'])
            # Получаем данные запроса на расписание по полученным данным формы.
            # Правила отображения дисциплин применяются для залогиненных
            # (и для гостей — только правила с галочкой «применять и для гостей»)
            if data['chosen_teacher']:
                data['table_query'] = get_table_query_for_teacher_by_dates(
                    data['chosen_teacher'], dates,
                    viewer_is_authenticated=request.user.is_authenticated)
        except Exception as e:
            for error_msg in get_error_messages(e):
                messages.error(request, error_msg)
        return render(request, 'main/guest/GuestViewScheduleByTeacherPage.html', context=data)


def render_schedule_by_auditorium_page(request):
    if request.method == "GET":
        data = util.get_data_for_schedule()
        data['chosen_auditorium'], error = _get_or_default(
            auditorium_service.get_by_pk,
            request.GET.get('chosen_auditorium'),
            data['auditoriums'],
            "аудитория")
        if error:
            messages.error(request, error)
        # Получаем временные данные
        data['chosen_date_start'] = request.GET.get('chosen_date_start', util.get_today_date())
        data['chosen_date_end'] = request.GET.get('chosen_date_end', util.get_next_date())
        # Проверяем по полученным данным формы, какой запрос нам необходимо выполнить
        try:
            validate_input_dates_presented_and_correct(data['chosen_date_start'], data['chosen_date_end'])
            dates = get_dates_for_table_query(data['chosen_date_start'], data['chosen_date_end'])
            if data['chosen_auditorium']:
                data['table_query'] = get_table_query_for_auditorium_by_dates(data['chosen_auditorium'], dates)
        except Exception as e:
            for error_msg in get_error_messages(e):
                messages.error(request, error_msg)
        return render(request, 'main/guest/GuestViewScheduleByAuditoriumPage.html', context=data)

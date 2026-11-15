"""Экспорт выбранного расписания в Word / Excel / PDF.

Два режима (доступны всем, в том числе гостям):
- без дат — официальная сетка семестра по постоянному расписанию
  (выбранная группа / преподаватель / аудитория);
- с параметрами date_from/date_to — полное расписание за период:
  постоянное расписание и замены, развёрнутые по датам, как на страницах просмотра.
"""
from django.http import HttpResponse

from ..models import Auditorium, Group, Teacher
from ..services import export_service, util

MAX_EXPORT_RANGE_DAYS = 30


def _error(message, status=400):
    return HttpResponse(f'<h3>Ошибка экспорта</h3><p>{message}</p>'
                        f'<p><a href="/">Вернуться на сайт</a></p>',
                        status=status)


def _parse_export_dates(request):
    """Даты «за период» из запроса: (список дат, None) либо (None, текст ошибки).

    Обе даты обязательны; интервал — не больше MAX_EXPORT_RANGE_DAYS дней
    (как у страниц просмотра). Если дат нет вовсе — (None, None): режим
    «сетка семестра».
    """
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    if not date_from and not date_to:
        return None, None
    if not date_from or not date_to:
        return None, 'Для экспорта за период укажите обе даты — начальную и конечную'
    try:
        start = util.convert_string_to_date(date_from)
        end = util.convert_string_to_date(date_to)
    except ValueError:
        return None, 'Некорректный формат даты (ожидается ГГГГ-ММ-ДД)'
    if start > end:
        return None, 'Некорректный интервал - конечная дата идет раньше начальной'
    if (end - start).days > MAX_EXPORT_RANGE_DAYS:
        return None, (f'Слишком большой интервал - выберите интервал '
                      f'не больше {MAX_EXPORT_RANGE_DAYS} календарных дней')
    return util.get_dates(start, end), None


def export_schedule(request):
    """?type=group|teacher|auditorium&id=<pk>&format=xlsx|docx|pdf
    и дополнительно ?date_from=ГГГГ-ММ-ДД&date_to=ГГГГ-ММ-ДД (экспорт за период)."""
    export_type = request.GET.get('type', '')
    file_format = request.GET.get('format', '')
    object_id = request.GET.get('id', '')

    if file_format not in export_service.BUILDERS:
        return _error('Неизвестный формат файла. Доступны: xlsx, docx, pdf.')

    dates, date_error = _parse_export_dates(request)
    if date_error:
        return _error(date_error)

    if export_type == 'group':
        try:
            group = Group.objects.get(pk=object_id)
        except (Group.DoesNotExist, ValueError):
            return _error('Группа не найдена.', status=404)
        if dates is None:
            grid = export_service.build_grid_for_group(group)
            file_title = f'{group.title}_{grid["year_short"]}'
        else:
            grid = export_service.build_date_range_grid_for_group(group, dates)
            file_title = f'{group.title}_{grid["period"]}'
    elif export_type == 'teacher':
        try:
            teacher = Teacher.objects.get(pk=object_id)
        except (Teacher.DoesNotExist, ValueError):
            return _error('Преподаватель не найден.', status=404)
        # правила отображения дисциплин применяются так же, как на странице
        if dates is None:
            grid = export_service.build_grid_for_teacher(
                teacher, viewer_is_authenticated=request.user.is_authenticated)
            file_title = f'Преподаватель_{teacher.name}_{grid["year_short"]}'
        else:
            grid = export_service.build_date_range_grid_for_teacher(
                teacher, dates, viewer_is_authenticated=request.user.is_authenticated)
            file_title = f'Преподаватель_{teacher.name}_{grid["period"]}'
    elif export_type == 'auditorium':
        try:
            auditorium = Auditorium.objects.get(pk=object_id)
        except (Auditorium.DoesNotExist, ValueError):
            return _error('Аудитория не найдена.', status=404)
        if dates is None:
            grid = export_service.build_grid_for_auditorium(auditorium)
            file_title = f'Аудитория_{auditorium.number}_{grid["year_short"]}'
        else:
            grid = export_service.build_date_range_grid_for_auditorium(auditorium, dates)
            file_title = f'Аудитория_{auditorium.number}_{grid["period"]}'
    else:
        return _error('Неизвестный тип расписания. Доступны: group, teacher, auditorium.')

    try:
        if dates is None:
            return export_service.export_schedule(grid, file_format, file_title)
        if not grid['days']:
            return _error('В выбранном диапазоне занятий не найдено')
        return export_service.export_date_range_schedule(grid, file_format, file_title)
    except RuntimeError as e:
        return _error(str(e))

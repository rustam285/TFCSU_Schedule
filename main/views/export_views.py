"""Экспорт выбранного расписания в Word / Excel / PDF (официальная сетка семестра).

Доступен всем пользователям (в том числе гостям) — как и страницы просмотра.
Экспортируется семестровая сетка постоянного расписания для выбранной
группы / преподавателя / аудитории.
"""
from django.http import HttpResponse

from ..models import Auditorium, Group, Teacher
from ..services import export_service


def _error(message, status=400):
    return HttpResponse(f'<h3>Ошибка экспорта</h3><p>{message}</p>'
                        f'<p><a href="/">Вернуться на сайт</a></p>',
                        status=status)


def export_schedule(request):
    """?type=group|teacher|auditorium&id=<pk>&format=xlsx|docx|pdf"""
    export_type = request.GET.get('type', '')
    file_format = request.GET.get('format', '')
    object_id = request.GET.get('id', '')

    if file_format not in export_service.BUILDERS:
        return _error('Неизвестный формат файла. Доступны: xlsx, docx, pdf.')

    if export_type == 'group':
        try:
            group = Group.objects.get(pk=object_id)
        except (Group.DoesNotExist, ValueError):
            return _error('Группа не найдена.', status=404)
        grid = export_service.build_grid_for_group(group)
        file_title = f'{group.title}_{grid["year_short"]}'
    elif export_type == 'teacher':
        try:
            teacher = Teacher.objects.get(pk=object_id)
        except (Teacher.DoesNotExist, ValueError):
            return _error('Преподаватель не найден.', status=404)
        # правила отображения дисциплин применяются так же, как на странице
        grid = export_service.build_grid_for_teacher(
            teacher, viewer_is_authenticated=request.user.is_authenticated)
        file_title = f'Преподаватель_{teacher.name}_{grid["year_short"]}'
    elif export_type == 'auditorium':
        try:
            auditorium = Auditorium.objects.get(pk=object_id)
        except (Auditorium.DoesNotExist, ValueError):
            return _error('Аудитория не найдена.', status=404)
        grid = export_service.build_grid_for_auditorium(auditorium)
        file_title = f'Аудитория_{auditorium.number}_{grid["year_short"]}'
    else:
        return _error('Неизвестный тип расписания. Доступны: group, teacher, auditorium.')

    try:
        return export_service.export_schedule(grid, file_format, file_title)
    except RuntimeError as e:
        return _error(str(e))

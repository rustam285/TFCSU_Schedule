from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse

from main.models import TeacherDisciplineRule
from main.services import teacher_service, discipline_service, teacher_rule_service
from main.services.util import get_error_messages


@login_required
def render_teacher_rules_page(request):
    data = {
        'teachers': teacher_service.get_all(),
        'disciplines': discipline_service.get_all(),
        'modes': TeacherDisciplineRule.Mode.choices,
    }

    chosen_teacher_id = request.GET.get('chosen_teacher') or request.POST.get('chosen_teacher')
    chosen_teacher = None
    if chosen_teacher_id:
        try:
            chosen_teacher = teacher_service.get_by_pk(chosen_teacher_id)
        except Exception:
            messages.error(request, "Выбранный преподаватель не найден")
    elif data['teachers']:
        chosen_teacher = data['teachers'].first()
    data['chosen_teacher'] = chosen_teacher

    if chosen_teacher:
        data['rules'] = teacher_rule_service.get_rules_for_teacher(chosen_teacher)

    if request.method == "POST":
        if request.POST.get('delete_rule_id'):
            if teacher_rule_service.delete_rule_by_pk(int(request.POST.get('delete_rule_id'))):
                messages.success(request, "Правило удалено")
            else:
                messages.error(request, "Правило не найдено")
        elif request.POST.get('add_rule'):
            discipline_id = request.POST.get('discipline')
            mode = request.POST.get('mode')
            apply_for_guests = bool(request.POST.get('apply_for_guests'))
            try:
                if not chosen_teacher:
                    raise ValueError("Сначала выберите преподавателя")
                discipline = discipline_service.get_by_pk(discipline_id)
                if mode not in (TeacherDisciplineRule.Mode.SHOW, TeacherDisciplineRule.Mode.HIDE):
                    raise ValueError("Некорректный режим правила")
                rule, created = teacher_rule_service.add_rule(
                    chosen_teacher, discipline, mode, apply_for_guests)
                messages.success(
                    request,
                    f"Правило {'добавлено' if created else 'обновлено'}: "
                    f"{discipline.title} — "
                    f"{'показывать дополнительно' if mode == TeacherDisciplineRule.Mode.SHOW else 'скрывать'}")
            except Exception as e:
                for error in get_error_messages(e):
                    messages.error(request, error)
        return redirect(f"{reverse('teacher_rules')}?chosen_teacher={chosen_teacher.id}"
                        if chosen_teacher else reverse('teacher_rules'))

    return render(request, 'main/teacher/TeacherRulesPage.html', context=data)

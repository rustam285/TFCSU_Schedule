from main.models import TeacherDisciplineRule


def get_rules_for_teacher(teacher):
    return (TeacherDisciplineRule.objects
            .filter(teacher=teacher)
            .select_related('discipline')
            .order_by('mode', 'discipline__title'))


def get_filtered_discipline_ids(teacher, viewer_is_authenticated: bool) -> tuple[list[int], list[int]]:
    """Возвращает (shown_ids, hidden_ids) по правилам преподавателя.

    Для не залогиненных пользователей применяются только правила
    с apply_for_guests=True (см. beseda.md: спец-расписание показывалось
    только при is_login).
    """
    rules = TeacherDisciplineRule.objects.filter(teacher=teacher)
    if not viewer_is_authenticated:
        rules = rules.filter(apply_for_guests=True)
    shown = [r.discipline_id for r in rules if r.mode == TeacherDisciplineRule.Mode.SHOW]
    hidden = [r.discipline_id for r in rules if r.mode == TeacherDisciplineRule.Mode.HIDE]
    return shown, hidden


def add_rule(teacher, discipline, mode, apply_for_guests: bool) -> tuple[TeacherDisciplineRule, bool]:
    """Создаёт или обновляет правило (уникальность: преподаватель + дисциплина + режим)."""
    return TeacherDisciplineRule.objects.update_or_create(
        teacher=teacher,
        discipline=discipline,
        mode=mode,
        defaults={'apply_for_guests': apply_for_guests},
    )


def delete_rule_by_pk(pk) -> bool:
    deleted, _ = TeacherDisciplineRule.objects.filter(pk=pk).delete()
    return deleted > 0

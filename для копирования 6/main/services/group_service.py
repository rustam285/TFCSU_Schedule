from main.models import Group


def get_all():
    return Group.objects.all().order_by('course').order_by('title')


def get_by_form_of_education(form):
    return Group.objects.filter(form_of_education=form)


def get_by_pk(pk):
    return Group.objects.get(pk=pk)


def delete_by_pk(pk):
    get_by_pk(pk).delete()


def is_exists_by_title(title):
    return Group.objects.filter(title=title).exists()


def get_by_title(title):
    return Group.objects.filter(title=title).first()


def get_sorted_by_form_with_updated_at():
    """Группы, сгруппированные по форме обучения, с датой последнего изменения
    расписания (updated_at_display: 'дд.мм.гггг чч:мм' или '—')."""
    from django.utils import timezone

    result = []
    for form_value, form_label in Group.FormOfEducation.choices:
        groups = list(get_by_form_of_education(form_value).order_by('course', 'title'))
        for group in groups:
            group.updated_at_display = (
                timezone.localtime(group.updated_at).strftime('%d.%m.%Y %H:%M')
                if group.updated_at else '—')
        if groups:
            result.append({'form_label': form_label, 'groups': groups})
    return result

from django import template

from main.services import util

register = template.Library()


@register.inclusion_tag('components/search_form.html')
def render_search_form(query='', placeholder='Поиск...'):
    return {'query': query, 'placeholder': placeholder}


@register.inclusion_tag('components/group_updated_at_list.html')
def render_group_updated_at_list(groups_by_form):
    return {'groups_by_form': groups_by_form}


@register.inclusion_tag('components/pagination.html')
def render_pagination(page_obj, query=''):
    return {'page_obj': page_obj, 'query': query}


@register.inclusion_tag('components/modal.html')
def render_modal(modal_id, url_name, title, body_text, button_text, button_name, button_value,
                 chosen_group=None, chosen_day=None, chosen_week=None, chosen_date=None, return_to_main=False,
                 chosen_date_start=None, chosen_date_end=None):
    return {
        'modal_id': modal_id,
        'url_name': url_name,
        'title': title,
        'body_text': body_text,
        'button_text': button_text,
        'button_name': button_name,
        'button_value': button_value,
        'chosen_group': chosen_group,
        'chosen_day': chosen_day,
        'chosen_week': chosen_week,
        'chosen_date': chosen_date,
        'return_to_main': return_to_main,
        'chosen_date_start': chosen_date_start,
        'chosen_date_end': chosen_date_end,
    }


@register.inclusion_tag('components/dropdown-right.html')
def render_right_dropdown(button_text, dropdown_items, disabled=False):
    return {
        'button_text': button_text,
        'dropdown_items': dropdown_items,
        'disabled': disabled,
    }


@register.inclusion_tag('components/forms/add_full_time_schedule_form.html')
def render_add_schedule_form(add_lesson_data, group, groups, week_days, week_numbers, chosen_day=None, chosen_week=None,
                             chosen_date=None, chosen_date_start=None, chosen_date_end=None):
    data = {
        'add_lesson_data': add_lesson_data,
        'groups': groups,
        'week_days': week_days,
        'week_numbers': week_numbers
    }
    try:
        if group:
            data['form_of_education'] = group.form_of_education
            data['chosen_group'] = group.id
            data['group'] = group
    except AttributeError:
        pass
    if chosen_day:
        data['chosen_day'] = chosen_day
        data['chosen_week'] = chosen_week
    else:
        data['chosen_date'] = chosen_date
        data['chosen_date_start'] = chosen_date_start
        data['chosen_date_end'] = chosen_date_end
    return data


@register.inclusion_tag('components/lesson_edit_delete_button.html')
def render_lesson_edit_delete_button(button_type, group, slot, chosen_date_start=None, chosen_date_end=None, return_to_main=True):
    data = {
        'button_type': button_type,
        'form_of_education': group.form_of_education,
        'lesson_id': slot.lesson.id,
        'chosen_group_id': group.id,
        'slot': slot,
        'chosen_date_start': chosen_date_start,
        'chosen_date_end': chosen_date_end,
        'return_to_main': return_to_main
    }
    try:
        if slot.date:
            data['date_label'] = util.convert_date_to_string(slot.date)
    except AttributeError:
        pass
    return data


@register.inclusion_tag('components/tables/schedule_table.html')
def render_schedule_table(group, schedule_query):
    return {
        'group': group,
        'schedule_query': schedule_query,
    }


@register.inclusion_tag('components/tables/schedule_table_for_group.html')
def render_schedule_table_for_group(group, table_query):
    return {
        'group': group,
        'table_query': table_query,
    }


@register.inclusion_tag('components/tables/schedule_table_for_teacher.html')
def render_schedule_table_for_teacher(teacher, query):
    return {
        'teacher': teacher,
        'query': query,
    }


@register.inclusion_tag('components/tables/schedule_table_for_auditorium.html')
def render_schedule_table_for_auditorium(auditorium, table_query):
    return {
        'auditorium': auditorium,
        'table_query': table_query,
    }


@register.inclusion_tag('components/tables/admin_schedule_table.html')
def render_admin_schedule_table(add_lesson_data, group, groups, week_days, week_numbers, schedule_query,
                                chosen_day=None, chosen_week=None, chosen_date_start=None, chosen_date_end=None):
    data = {
        'group': group,
        'groups': groups,
        'week_days': week_days,
        'week_numbers': week_numbers,
        'add_lesson_data': add_lesson_data,
        'schedule_query': schedule_query,
    }
    if chosen_date_start:
        data['chosen_date_start'] = chosen_date_start
        data['chosen_date_end'] = chosen_date_end
    else:
        data['chosen_day'] = chosen_day
        data['chosen_week'] = chosen_week
    return data


@register.inclusion_tag('components/tables/teacher_table.html')
def render_teacher_table(teachers, height="0px"):
    return {
        'teachers': teachers,
        'height': height,
    }


@register.inclusion_tag('components/tables/group_table.html')
def render_group_table(groups, height="0px"):
    return {
        'groups': groups,
        'height': height,
    }


@register.inclusion_tag('components/tables/faculty_table.html')
def render_faculty_table(faculties, height="0px"):
    return {
        'faculties': faculties,
        'height': height,
    }


@register.inclusion_tag('components/tables/auditory_table.html')
def render_auditory_table(auditories, height="0px"):
    return {
        'auditories': auditories,
        'height': height,
    }


@register.inclusion_tag('components/tables/discipline_table.html')
def render_discipline_table(disciplines, height="0px"):
    return {
        'disciplines': disciplines,
        'height': height,
    }

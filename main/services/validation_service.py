from django.core.exceptions import ValidationError

from main.services import group_service, discipline_service, teacher_service, auditorium_service, util


def validate_input_dates_presented_and_correct(start_date, end_date):
    validation_errors = []
    if start_date == '' and end_date == '':
        validation_errors.append("Даты не выбраны")
    if not (start_date == '' or end_date == ''):
        if util.convert_string_to_date(start_date) > util.convert_string_to_date(end_date):
            validation_errors.append("Некорректный интервал - конечная дата идет раньше начальной")
        if (util.convert_string_to_date(end_date) - util.convert_string_to_date(start_date)).days > 30:
            validation_errors.append("Слишком большой интервал - выберите интервал меньше 30 календарных дней")
    if len(validation_errors) > 0:
        raise ValidationError(validation_errors)


def validate_input_dates_correct(start_date, end_date):
    if not (start_date == '' or end_date == '' or start_date is None or end_date is None):
        if util.convert_string_to_date(start_date) > util.convert_string_to_date(end_date):
            raise ValidationError("Некорректный интервал - конечная дата идет раньше начальной")


def validate_import_input_values(group_title, week, day, number, discipline_title, teacher_name, auditorium_number):
    error_message_prefix = f'Пара в {day}, {week} недели, {group_title}, №{number}:\n'
    validation_errors = ''
    if not discipline_service.is_exists_by_title(discipline_title):
        validation_errors += f'в названии дисциплины ошибка или ее нет в базе({discipline_title});\n'
    if not teacher_service.is_exists_by_name(teacher_name):
        validation_errors += f'в имени преподавателя ошибка или его нет в базе({teacher_name});\n'
    if auditorium_number == '' or not auditorium_service.is_exists_by_number(auditorium_number):
        validation_errors += f'в номере аудитории ошибка или ее нет в базе({auditorium_number});\n'
    if len(validation_errors) > 0:
        raise ValidationError(f'{error_message_prefix}{validation_errors}')


def validate_import_group_title(group_title):
    if not group_service.is_exists_by_title(group_title):
        raise ValidationError(f'В названии группы ошибка или ее не существует: {group_title}')


def validate_imported_pt_lessons(lessons):
    validation_errors = []
    for date, lesson in lessons.items():
        for number, lesson_data in lesson.items():
            validation_error = f'{date}, №{number}: '
            for key, value in lesson_data.items():
                if key == "discipline":
                    if not discipline_service.is_exists_by_title(value):
                        validation_error += f'в названии дисциплины ошибка или ее нет в базе({value});\n'
                if key == "teacher":
                    if not teacher_service.is_exists_by_name(value):
                        validation_error += f'в имени преподавателя ошибка или его нет в базе({value});\n'
                if key == "auditorium":
                    if value == '' or not str(value).isdigit() or not auditorium_service.is_exists_by_number(
                            int(value)):
                        validation_error += f'в номере аудитории ошибка или ее нет в базе({value});\n'
            if validation_error != f'{date}, №{number}: ':
                validation_errors.append(validation_error)
    if len(validation_errors) > 0:
        raise ValidationError(validation_errors)

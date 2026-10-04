from django.db.models import Q

from main.forms import LessonForm
from main.models import TemporarySchedule
from main.services import lesson_service, util


# Метод выводит список занятий для группы по указанной дате
def get_by_group_and_date(needed_group, needed_date):
    return TemporarySchedule.objects.filter(
        date=needed_date, lesson__group=needed_group
    ).order_by('date', 'lesson__number')


def get_by_group(needed_group):
    return TemporarySchedule.objects.filter(
        lesson__group=needed_group
    ).order_by('date', 'lesson__number')


def update(updated_slot):
    updated_slot.save()


def get_by_pk(pk):
    return TemporarySchedule.objects.get(pk=pk)


def delete_lessons_by_date(date):
    slots = TemporarySchedule.objects.filter(date=date)
    for slot in slots:
        lesson_service.delete_by_pk(slot.lesson.id)


def get_query_for_table_for_teacher_by_date(teacher, date):
    query = []
    week = {'days': []}
    day = {'label': f'{util.reformat_date_string(date)}',
           'schedule': TemporarySchedule.objects.filter(
               lesson__teacher=teacher,
               date=date
           ).order_by('lesson__number')}
    day['length'] = len(day['schedule']) + 1
    if day['length'] == 1:
        day['weekend'] = 'Нет занятий'
    for slot in day['schedule']:
        slot.time = LessonForm().time[slot.lesson.number]
        slot.lesson.number = LessonForm().NUMBER_OF_LESSON_CHOICES[slot.lesson.number]
    week['days'].append(day)
    query.append(week)
    return query


def get_query_for_table_for_auditorium_by_date(auditorium, date):
    query = []
    week = {'days': []}
    day = {'label': f'{util.reformat_date_string(date)}',
           'schedule': TemporarySchedule.objects.filter(
               lesson__auditorium=auditorium,
               date=date
           ).order_by('lesson__number')}
    day['length'] = len(day['schedule']) + 1
    if day['length'] == 1:
        day['weekend'] = 'Нет занятий'
    for slot in day['schedule']:
        slot.time = LessonForm().time[slot.lesson.number]
        slot.lesson.number = LessonForm().NUMBER_OF_LESSON_CHOICES[slot.lesson.number]
    week['days'].append(day)
    query.append(week)
    return query


def get_query_for_table_by_date(group, date):
    query = []
    week = {'days': []}
    day = {'label': f'{util.reformat_date_string(date)}',
           'schedule': TemporarySchedule.objects.filter(
               lesson__group=group,
               date=date
           ).order_by('lesson__number')}
    day['length'] = len(day['schedule']) + 1
    if day['length'] == 1:
        day['weekend'] = 'Выходной день'
    for slot in day['schedule']:
        slot.time = LessonForm().time[slot.lesson.number]
        slot.lesson.number = LessonForm().NUMBER_OF_LESSON_CHOICES[slot.lesson.number]
    week['days'].append(day)
    query.append(week)
    return query


def get_query_for_table_for_teacher_by_dates(teacher, start_date, end_date):
    query = []
    week = {'days': []}
    dates = TemporarySchedule.objects.filter(lesson__teacher=teacher,
                                             date__range=(start_date, end_date)
                                             ).values('date').order_by('date').distinct()
    for date in dates:
        day = {
            'label': util.reformat_date_string(util.convert_date_to_string(date['date'])),
            'schedule': TemporarySchedule.objects.filter(
                lesson__teacher=teacher,
                date=util.convert_date_to_string(date['date'])
            ).order_by('lesson__number')
        }
        day['length'] = len(day['schedule']) + 1
        if day['length'] == 1:
            day['weekend'] = 'Нет занятий'
        for slot in day['schedule']:
            slot.time = LessonForm().time[slot.lesson.number]
            slot.lesson.number = LessonForm().NUMBER_OF_LESSON_CHOICES[slot.lesson.number]
        week['days'].append(day)
    query.append(week)
    return query


def get_query_for_table_for_auditorium_by_dates(auditorium, start_date, end_date):
    query = []
    week = {'days': []}
    dates = TemporarySchedule.objects.filter(lesson__auditorium=auditorium,
                                             date__range=(start_date, end_date)
                                             ).values('date').order_by('date').distinct()
    for date in dates:
        day = {
            'label': util.reformat_date_string(util.convert_date_to_string(date['date'])),
            'schedule': TemporarySchedule.objects.filter(
                lesson__auditorium=auditorium,
                date=util.convert_date_to_string(date['date'])
            ).order_by('lesson__number')
        }
        day['length'] = len(day['schedule']) + 1
        if day['length'] == 1:
            day['weekend'] = 'Нет занятий'
        for slot in day['schedule']:
            slot.time = LessonForm().time[slot.lesson.number]
            slot.lesson.number = LessonForm().NUMBER_OF_LESSON_CHOICES[slot.lesson.number]
        week['days'].append(day)
    query.append(week)
    return query


def get_query_for_table_by_dates(group, start_date, end_date):
    query = []
    week = {'days': []}
    dates = TemporarySchedule.objects.filter(lesson__group=group,
                                             date__range=(start_date, end_date)
                                             ).values('date').order_by('date').distinct()
    for date in dates:
        day = {
            'label': util.reformat_date_string(util.convert_date_to_string(date['date'])),
            'schedule': TemporarySchedule.objects.filter(
                lesson__group=group,
                date=util.convert_date_to_string(date['date'])
            ).order_by('lesson__number')
        }
        day['length'] = len(day['schedule']) + 1
        if day['length'] == 1:
            day['weekend'] = 'Выходной день'
        for slot in day['schedule']:
            slot.time = LessonForm().time[slot.lesson.number]
            slot.lesson.number = LessonForm().NUMBER_OF_LESSON_CHOICES[slot.lesson.number]
        week['days'].append(day)
    query.append(week)
    return query

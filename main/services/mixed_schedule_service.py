import datetime

from main.models import TemporarySchedule
from main.services import group_service, lesson_service

def delete_lessons_by_date_and_group(date, lesson_group):
    slots = TemporarySchedule.objects.filter(date=date, lesson__group=lesson_group)
    for slot in slots:
        lesson_service.delete_by_pk(slot.lesson.id)

def delete_mixed_schedule_by_date_interval(lesson_group, start_date, end_date):
    iter_date = start_date
    while iter_date != end_date + datetime.timedelta(days=1):
        delete_lessons_by_date_and_group(iter_date, group_service.get_by_title(lesson_group))
        iter_date += datetime.timedelta(days=1)

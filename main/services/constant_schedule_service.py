from datetime import datetime

from django.db.models import QuerySet, F, Value, DateField, IntegerField, When, Case, Q

from main.forms import LessonForm
from main.models import ConstantSchedule, Teacher, TemporarySchedule
from main.services import teacher_rule_service
from main.services.util import get_week_number, get_weekday_by_date, convert_date_to_string, reformat_date_string


def get_const_schedule_by_date(date: datetime.date, group_id: int = None, teacher_id: int = None,
                               auditorium_id: int = None,
                               shown_discipline_ids: list[int] = None,
                               hidden_discipline_ids: list[int] = None) -> QuerySet:
    if group_id:
        return ConstantSchedule.objects.filter(
            lesson__group=group_id,
            week_day=LessonForm().week_day[get_weekday_by_date(date)][0],
            week_number=get_week_number(date)
        )
    if teacher_id:
        # Пары преподавателя + «прикреплённые» дисциплины (вне зависимости,
        # за кем они числятся в базе), минус скрытые дисциплины
        query = ConstantSchedule.objects.filter(
            Q(lesson__teacher=teacher_id)
            | Q(lesson__discipline__in=shown_discipline_ids or []),
            week_day=LessonForm().week_day[get_weekday_by_date(date)][0],
            week_number=get_week_number(date)
        )
        if hidden_discipline_ids:
            query = query.exclude(lesson__discipline__in=hidden_discipline_ids)
        return query
    if auditorium_id:
        return ConstantSchedule.objects.filter(
            lesson__auditorium=auditorium_id,
            week_day=LessonForm().week_day[get_weekday_by_date(date)][0],
            week_number=get_week_number(date)
        )


def get_const_schedule_for_group_by_week_and_weekday(group_id: int, week: 1 | 2,
                                                     weekday: ConstantSchedule.WeekDay) -> QuerySet:
    return ConstantSchedule.objects.filter(
        lesson__group=group_id,
        week_day=weekday,
        week_number=week
    )


def get_const_schedule_for_group(group_id: int) -> QuerySet:
    weekday_order = [
        When(week_day=ConstantSchedule.WeekDay.MONDAY, then=Value(1)),
        When(week_day=ConstantSchedule.WeekDay.TUESDAY, then=Value(2)),
        When(week_day=ConstantSchedule.WeekDay.WEDNESDAY, then=Value(3)),
        When(week_day=ConstantSchedule.WeekDay.THURSDAY, then=Value(4)),
        When(week_day=ConstantSchedule.WeekDay.FRIDAY, then=Value(5)),
        When(week_day=ConstantSchedule.WeekDay.SATURDAY, then=Value(6)),
        When(week_day=ConstantSchedule.WeekDay.SUNDAY, then=Value(7)),
    ]
    return ConstantSchedule.objects.filter(
        lesson__group=group_id
    ).annotate(
        weekday_num=Case(*weekday_order, output_field=IntegerField())
    ).order_by('week_number', 'weekday_num', 'lesson__number')


def get_temp_schedule_by_date(date: datetime.date, group_id: int = None, teacher_id: int = None,
                              auditorium_id: int = None,
                              shown_discipline_ids: list[int] = None,
                              hidden_discipline_ids: list[int] = None) -> QuerySet:
    if group_id:
        return TemporarySchedule.objects.filter(
            lesson__group=group_id,
            date=convert_date_to_string(date)
        )
    if teacher_id:
        # Пары преподавателя + «прикреплённые» дисциплины, минус скрытые
        query = TemporarySchedule.objects.filter(
            Q(lesson__teacher=teacher_id)
            | Q(lesson__discipline__in=shown_discipline_ids or []),
            date=convert_date_to_string(date)
        )
        if hidden_discipline_ids:
            query = query.exclude(lesson__discipline__in=hidden_discipline_ids)
        return query
    if auditorium_id:
        return TemporarySchedule.objects.filter(
            lesson__auditorium=auditorium_id,
            date=convert_date_to_string(date)
        )


def union_const_and_temp_schedule_by_date(temp_schedule: QuerySet, const_schedule: QuerySet,
                                          date: datetime.date) -> QuerySet:
    # temp_lesson_numbers = temp_schedule.values_list('lesson__number', flat=True)
    # const_schedule = const_schedule.exclude(lesson__number__in=temp_lesson_numbers)
    temp_schedule = temp_schedule.annotate(
        lesson_number=F('lesson__number'),
        is_special=F('lesson__is_special'),
        discipline=F('lesson__discipline__title'),
        format=F('lesson__format'),
        group=F('lesson__group__title'),
        teacher_name=F('lesson__teacher__name'),
        teacher_title=F('lesson__teacher__title'),
        auditorium=F('lesson__auditorium__number'),
    )
    const_schedule = const_schedule.annotate(
        lesson_number=F('lesson__number'),
        is_special=F('lesson__is_special'),
        discipline=F('lesson__discipline__title'),
        format=F('lesson__format'),
        group=F('lesson__group__title'),
        teacher_name=F('lesson__teacher__name'),
        teacher_title=F('lesson__teacher__title'),
        auditorium=F('lesson__auditorium__number'),
        date=Value(date, output_field=DateField()))
    return temp_schedule.union(const_schedule).order_by('lesson_number').values()


def get_schedule_object(schedule: QuerySet):
    try:
        current = schedule[0]
    except IndexError:
        return {
            "type": "schedule",
            "data": [{
                "number": "",
                "time": "",
                "lesson_label": "Нет занятий",
                "auditorium": ""
            }]
        }
    data = []
    for slot in schedule:
        data.append({
            "number": LessonForm().NUMBER_OF_LESSON_CHOICES[slot["lesson_number"]],
            "time": LessonForm().time[slot["lesson_number"]],
            "lesson_label": f"{"*" if slot["is_special"] else ""}"
                            f"{slot["discipline"]}"
                            f"{" (" + slot["format"] + ")" if slot["format"] != "" else ""}"
                            f"{", " + slot["teacher_name"]}"
                            f"{", " + slot["teacher_title"] if slot["teacher_title"] != "" else ""}",
            "auditorium": slot["auditorium"]
        })
    return {
        "type": "schedule",
        "data": data
    }


def get_schedule_object_for_auditorium(schedule: QuerySet):
    try:
        current = schedule[0]
    except IndexError:
        return {
            "type": "schedule",
            "data": [{
                "number": "",
                "time": "",
                "lesson_label": "Нет занятий",
                "auditorium": ""
            }]
        }
    data = []
    for slot in schedule:
        data.append({
            "number": LessonForm().NUMBER_OF_LESSON_CHOICES[slot["lesson_number"]],
            "time": LessonForm().time[slot["lesson_number"]],
            "lesson_label": f"{"*" if slot["is_special"] else ""}"
                            f"{slot["discipline"]}"
                            f"{" (" + slot["format"] + ")" if slot["format"] != "" else ""}"
                            f"{", " + slot["teacher_name"]}"
                            f"{", " + slot["teacher_title"] if slot["teacher_title"] != "" else ""}",
            "auditorium": slot["group"]
        })
    return {
        "type": "schedule",
        "data": data
    }


def get_schedule_object_for_teacher(schedule: QuerySet):
    try:
        current = schedule[0]
    except IndexError:
        return {
            "type": "schedule",
            "data": [{
                "number": "",
                "time": "",
                "lesson_label": "Нет занятий",
                "auditorium": ""
            }]
        }
    data = []
    obj = {
        "number": LessonForm().NUMBER_OF_LESSON_CHOICES[schedule[0]["lesson_number"]],
        "time": LessonForm().time[schedule[0]["lesson_number"]],
        "lesson_label": f"{"*" if schedule[0]["is_special"] else ""}"
                        f"{schedule[0]["discipline"]}"
                        f"{" (" + schedule[0]["format"] + ")" if schedule[0]["format"] != "" else ""}",
        "auditorium": schedule[0]["auditorium"]
    }
    for slot in schedule:
        if (slot["lesson_number"] == current["lesson_number"]
                and slot["discipline"] == current["discipline"]
                and slot["format"] == current["format"]
                and slot["auditorium"] == current["auditorium"]):
            obj['lesson_label'] += f"{", " + slot["group"]}"
        else:
            current = slot
            data.append(obj)
            obj = {
                "number": LessonForm().NUMBER_OF_LESSON_CHOICES[slot["lesson_number"]],
                "time": LessonForm().time[slot["lesson_number"]],
                "lesson_label": f"{"*" if slot["is_special"] else ""}"
                                f"{slot["discipline"]}"
                                f"{" (" + slot["format"] + ")" if slot["format"] != "" else ""}"
                                f"{", " + slot["group"]}",
                "auditorium": slot["auditorium"]
            }
    data.append(obj)
    return {
        "type": "schedule",
        "data": data
    }


def get_by_time(needed_day=None, needed_week=None):
    # Получаем список занятий
    if not needed_week:
        return ConstantSchedule.objects.filter(
            week_day=needed_day
        ).order_by('lesson__number')
    elif not needed_day:
        return ConstantSchedule.objects.filter(
            week_number=needed_week
        ).order_by('lesson__number')

    lessons_by_time = ConstantSchedule.objects.filter(
        week_day=needed_day,
        week_number=needed_week
    ).order_by('lesson__number')
    return lessons_by_time


def get_query_for_table(group, week_days, week_numbers):
    week_days = week_days.split()
    week_numbers = week_numbers.split()
    query = []
    for week_number in week_numbers:
        week = {'label': f'{week_number} неделя', 'days': []}
        for week_day in week_days:
            day = {'label': f'{dict(LessonForm().week_day).get(week_day)}',
                   'schedule': ConstantSchedule.objects.filter(
                       lesson__group=group,
                       week_day=week_day,
                       week_number=week_number
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


def get_week_object(date: datetime.date):
    return {
        "type": "week",
        "data": f"{get_week_number(date)} неделя"
    }


def get_day_object(date: datetime.date):
    return {
        "type": "day",
        "data": f"{LessonForm().week_day[get_weekday_by_date(date)][1]}, {reformat_date_string(convert_date_to_string(date))}"
    }


def get_table_query_for_group_by_dates(group_id: int, dates: list[datetime.date]):
    table_query = []
    current_date_week = dates[0].isocalendar().week
    table_query.append(get_week_object(dates[0]))
    for date in dates:
        if current_date_week != date.isocalendar().week:
            current_date_week = date.isocalendar().week
            table_query.append(get_week_object(date))
        table_query.append(get_day_object(date))
        temp = get_temp_schedule_by_date(date, group_id)
        const = get_const_schedule_by_date(date, group_id)
        table_query.append(get_schedule_object(union_const_and_temp_schedule_by_date(temp, const, date)))
    return table_query


def get_table_query_for_teacher_by_dates(teacher_id: int, dates: list[datetime.date],
                                         viewer_is_authenticated: bool = False):
    shown_ids, hidden_ids = teacher_rule_service.get_filtered_discipline_ids(teacher_id, viewer_is_authenticated)
    table_query = []
    current_date_week = dates[0].isocalendar().week
    table_query.append(get_week_object(dates[0]))
    for date in dates:
        if current_date_week != date.isocalendar().week:
            current_date_week = date.isocalendar().week
            table_query.append(get_week_object(date))
        table_query.append(get_day_object(date))
        temp = get_temp_schedule_by_date(date, teacher_id=teacher_id,
                                         shown_discipline_ids=shown_ids,
                                         hidden_discipline_ids=hidden_ids)
        const = get_const_schedule_by_date(date, teacher_id=teacher_id,
                                           shown_discipline_ids=shown_ids,
                                           hidden_discipline_ids=hidden_ids)
        table_query.append(get_schedule_object_for_teacher(union_const_and_temp_schedule_by_date(temp, const, date)))
    return table_query


def get_table_query_for_auditorium_by_dates(auditorium_id: int, dates: list[datetime.date]):
    table_query = []
    current_date_week = dates[0].isocalendar().week
    table_query.append(get_week_object(dates[0]))
    for date in dates:
        if current_date_week != date.isocalendar().week:
            current_date_week = date.isocalendar().week
            table_query.append(get_week_object(date))
        table_query.append(get_day_object(date))
        temp = get_temp_schedule_by_date(date, auditorium_id=auditorium_id)
        const = get_const_schedule_by_date(date, auditorium_id=auditorium_id)
        table_query.append(get_schedule_object_for_auditorium(union_const_and_temp_schedule_by_date(temp, const, date)))
    return table_query


def get_query_for_table_by_auditorium(auditorium, week_days, week_numbers):
    week_days = week_days.split()
    week_numbers = week_numbers.split()
    query = []
    for week_number in week_numbers:
        week = {'label': f'{week_number} неделя', 'days': []}
        for week_day in week_days:
            day = {'label': f'{dict(LessonForm().week_day).get(week_day)}',
                   'schedule': ConstantSchedule.objects.filter(
                       lesson__auditorium=auditorium,
                       week_day=week_day,
                       week_number=week_number
                   ).order_by('lesson__number')}
            day['length'] = len(day['schedule']) + 1
            if day['length'] == 1:
                day['weekend'] = 'Нет занятий'
            for slot in day['schedule']:
                slot.time = LessonForm().time[slot.lesson.number]
            week['days'].append(day)
        query.append(week)
    return query


def get_by_pk(pk):
    return ConstantSchedule.objects.get(pk=pk)


def update(updated_object):
    updated_object.save()

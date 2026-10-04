import pandas as pd
from django.contrib.auth.decorators import login_required
from django.db.models import F, Value, DateField, IntegerField, CharField, When, Case
from django.http import HttpResponse

from ..models import ConstantSchedule, TemporarySchedule


def get_query_for_export():
    weekday_order = [
        When(week_day=ConstantSchedule.WeekDay.MONDAY, then=Value(1)),
        When(week_day=ConstantSchedule.WeekDay.TUESDAY, then=Value(2)),
        When(week_day=ConstantSchedule.WeekDay.WEDNESDAY, then=Value(3)),
        When(week_day=ConstantSchedule.WeekDay.THURSDAY, then=Value(4)),
        When(week_day=ConstantSchedule.WeekDay.FRIDAY, then=Value(5)),
        When(week_day=ConstantSchedule.WeekDay.SATURDAY, then=Value(6)),
        When(week_day=ConstantSchedule.WeekDay.SUNDAY, then=Value(7)),
    ]
    const_schedule = ConstantSchedule.objects.all()
    temp_schedule = TemporarySchedule.objects.all()
    temp_schedule = temp_schedule.annotate(
        week_number=Value(None,
                          output_field=IntegerField(choices=ConstantSchedule.WeekNumber)),
        weekday_num=Value(None, output_field=IntegerField()),
        week_day=Value(None, output_field=CharField()),
        lesson_number=F('lesson__number'),
        is_special=F('lesson__is_special'),
        discipline=F('lesson__discipline__title'),
        format=F('lesson__format'),
        group=F('lesson__group__title'),
        teacher_name=F('lesson__teacher__name'),
        auditorium=F('lesson__auditorium__number'),
    )
    const_schedule = const_schedule.annotate(
        weekday_num=Case(*weekday_order, output_field=IntegerField()),
        date=Value(None, output_field=DateField()),
        lesson_number=F('lesson__number'),
        is_special=F('lesson__is_special'),
        discipline=F('lesson__discipline__title'),
        format=F('lesson__format'),
        group=F('lesson__group__title'),
        teacher_name=F('lesson__teacher__name'),
        auditorium=F('lesson__auditorium__number'),
    )
    return const_schedule.union(temp_schedule).order_by('date', 'week_number', 'weekday_num', 'lesson_number').values()


@login_required
def export_excel(request):
    data = pd.DataFrame(list(get_query_for_export()))
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="data.xlsx"'
    data.to_excel(response, index=False)
    return response

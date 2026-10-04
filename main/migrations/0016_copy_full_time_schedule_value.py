from django.db import migrations

WEEKDAY = {
    'Понедельник': 'пн',
    'Вторник': 'вт',
    'Среда': 'ср',
    'Четверг': 'чт',
    'Пятница': 'пт',
    'Суббота': 'сб',
    'Воскресенье': 'вс',
}


def copy_full_time_schedule_value(apps, schema_editor):
    FullTimeSchedule = apps.get_model('main', 'FullTimeSchedule')
    Lesson = apps.get_model('main', 'Lesson')
    Day = apps.get_model('main', 'Day')
    Week = apps.get_model('main', 'Week')
    for lesson in Lesson.objects.all():
        day_object = Day.objects.get(pk=lesson.day.id)
        week_object = Week.objects.get(pk=lesson.week.id)
        row = FullTimeSchedule(lesson=lesson, week_day=WEEKDAY[day_object.Name_Of_Day],
                               week_number=week_object.Number_Of_Week)
        row.save()


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0015_copy_group_value'),
    ]

    operations = [
        migrations.RunPython(copy_full_time_schedule_value)
    ]

from django.db import migrations


def copy_lesson_value(apps, schema_editor):
    Lesson = apps.get_model('main', 'Lesson')
    Subject = apps.get_model('main', 'Subject')
    Discipline = apps.get_model('main', 'Discipline')
    Preps = apps.get_model('main', 'Preps')
    Teacher = apps.get_model('main', 'Teacher')
    Aud = apps.get_model('main', 'Aud')
    Auditorium = apps.get_model('main', 'Auditorium')
    for row in Lesson.objects.all():
        row.number = row.Number_Of_Lesson
        if row.Code_Subj:
            subject_from_row = Subject.objects.get(pk=row.Code_Subj.id)
            row.format = subject_from_row.Type_Of_Subj
            row.discipline = Discipline.objects.filter(title=subject_from_row.Subj).first()
        if row.Code_Preps:
            preps_from_row = Preps.objects.get(pk=row.Code_Preps.id)
            row.teacher = Teacher.objects.filter(name=preps_from_row.Name_Of_Preps).first()
        if row.Code_Aud:
            aud_from_row = Aud.objects.get(pk=row.Code_Aud.id)
            row.auditorium = Auditorium.objects.filter(number=aud_from_row.Aud).first()
        row.render_all_groups_page = row.Code_Group
        row.save()


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0013_copying_models'),
    ]

    operations = [
        migrations.RunPython(copy_lesson_value)
    ]

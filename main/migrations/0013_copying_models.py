from django.db import migrations


def copy_teacher_value(apps, schema_editor):
    Teacher = apps.get_model('main', 'Teacher')
    Preps = apps.get_model('main', 'Preps')

    unique_subjects = Preps.objects.values_list('Name_Of_Preps', 'Rank_Of_Preps').distinct()
    for prep in unique_subjects:
        copy_row = Teacher(name=prep[0], title=prep[1])
        copy_row.save()


def copy_auditorium_value(apps, schema_editor):
    Auditorium = apps.get_model('main', 'Auditorium')
    Aud = apps.get_model('main', 'Aud')

    unique_subjects = Aud.objects.values_list('Corps', 'Aud').distinct()
    for aud in unique_subjects:
        copy_row = Auditorium(building=aud[0], number=aud[1])
        copy_row.save()



class Migration(migrations.Migration):
    dependencies = [
        ('main', '0012_copying_models'),
    ]

    operations = [
        migrations.RunPython(copy_teacher_value),
        migrations.RunPython(copy_auditorium_value),
    ]

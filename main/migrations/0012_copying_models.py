from django.db import migrations


def copy_discipline_value(apps, schema_editor):
    Discipline = apps.get_model('main', 'Discipline')
    Subject = apps.get_model('main', 'Subject')

    unique_subjects = Subject.objects.values_list('Subj', flat=True).distinct()
    for subj in unique_subjects:
        copy_row = Discipline(title=subj, )
        copy_row.save()


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0011_alter_field_faculty'),
    ]

    operations = [
        migrations.RunPython(copy_discipline_value)
    ]

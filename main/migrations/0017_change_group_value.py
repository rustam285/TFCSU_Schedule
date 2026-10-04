from django.db import migrations


def change_group_value(apps, schema_editor):
    Group = apps.get_model('main', 'Group')
    for row in Group.objects.all():
        row.course = row.old_course
        if row.old_form_of_education:
            if row.old_form_of_education == 'очная':
                row.form_of_education = 'о'
            if row.old_form_of_education == 'заочная':
                row.form_of_education = 'з'
            if row.old_form_of_education == 'очно-заочная':
                row.form_of_education = 'о-з'
        row.save()


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0016_copy_full_time_schedule_value'),
    ]

    operations = [
        migrations.RunPython(change_group_value)
    ]

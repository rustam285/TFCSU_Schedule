from django.db import migrations


def copy_group_value(apps, schema_editor):
    Group = apps.get_model('main', 'Group')
    for row in Group.objects.all():
        row.course = row.old_course
        if row.old_form_of_education:
            if row.old_form_of_education == 'очная':
                row.form_of_education = 'o'
            if row.old_form_of_education == 'заочная':
                row.form_of_education = 'з'
            if row.old_form_of_education == 'очно-заочная':
                row.form_of_education = 'о-з'
        row.title = row.Name_Of_Group
        row.save()


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0014_copy_lesson_value'),
    ]

    operations = [
        migrations.RunPython(copy_group_value)
    ]

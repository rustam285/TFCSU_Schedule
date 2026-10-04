from django.contrib import admin

from .models import (Auditorium, Faculty, Teacher,
                     Discipline, Group, Lesson, ConstantSchedule, TeacherDisciplineRule, SiteSetting)


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    search_fields = ('key',)


@admin.register(TeacherDisciplineRule)
class TeacherDisciplineRuleAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'discipline', 'mode', 'apply_for_guests')
    list_filter = ('mode', 'apply_for_guests')
    search_fields = ('teacher__name', 'discipline__title')


admin.site.register(Auditorium)
admin.site.register(Faculty)
admin.site.register(Teacher)
admin.site.register(Discipline)
admin.site.register(Group)
admin.site.register(Lesson)
admin.site.register(ConstantSchedule)

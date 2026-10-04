from django.urls import reverse_lazy

view_buttons = [
    ('Изменить (очное)', reverse_lazy('edit_schedule'), False),
    ('Постоянные', reverse_lazy('delete_schedule'), False),
    ('Временные', reverse_lazy('delete_part_time_schedule'), False),
]

ftf_buttons = [
    ('Импортировать (ВО)', reverse_lazy('import_schedule_vo'), False),
    ('Импортировать (СПО)', reverse_lazy('import_schedule_spo'), False)
]

ptf_buttons = [
    ('Импортировать', reverse_lazy('import_part_time_schedule'), False),
    ('Добавить вручную', reverse_lazy('add_part_time_schedule'), False)
]

mf_buttons = [
    ('Импортировать', reverse_lazy('import_mixed_schedule'), False),
    ('Добавить вручную', reverse_lazy('add_mixed_schedule'), False)
]

admin_check_schedule_buttons = [
    ('Посмотреть по группам', reverse_lazy('check_schedule_group'), False),
    ('Посмотреть по аудиториям', reverse_lazy('check_schedule_auditoriums'), False),
    ('Посмотреть по преподавателям', reverse_lazy('check_schedule_teachers'), False)
]

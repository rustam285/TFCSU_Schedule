from django.urls import path
from django.views.generic import RedirectView


from .views import schedule_views, auth_views, part_time_schedule_views, admin_views, guests_views, \
    teachers_views, group_views, faculty_view, auditory_views, discipline_views, mixed_schedule_views, \
    database_views, export_views, teacher_rule_views, backup_views, notification_views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # Юрл для входа и выхода
    path('login/', auth_views.LoginUser.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='guests'), name='logout'),

    # Юрл для гостей
    path('', guests_views.render_start_page, name='guests'),  # Стартовая страница
    # Просмотр расписания по группам
    path('schedule/group/', guests_views.render_schedule_by_group_page, name='guests_check_groups'),
    # Просмотр расписания по учителям
    path('schedule/teacher/', guests_views.render_schedule_by_teacher_page, name='guests_check_preps'),
    # Просмотр расписания по аудиториям
    path('schedule/auditorium/', guests_views.render_schedule_by_auditorium_page, name='guests_check_auds'),

    # Экспорт выбранного расписания в Word / Excel / PDF (доступен всем)
    path('export/schedule/', export_views.export_schedule, name='export_schedule'),

    # Юрл для администрации, должны включать admin/ в пути
    path('admin/home/', admin_views.render_start_page, name='home'),  # Стартовая страница

    # Страницы для учителей
    path('admin/teachers/', teachers_views.render_all_teachers_page, name='teachers'),  # Все учителя
    path('admin/add/teacher/', teachers_views.render_add_teacher_page, name='add_teachers'),  # Добавить
    path('admin/edit/teacher/', teachers_views.render_edit_teacher_page, name='edit_teachers'),  # Редактировать
    path('admin/delete/teacher/', teachers_views.render_delete_teacher_page, name='delete_teachers'),  # Удалить

    # Страницы для факультетов
    path('admin/faculty/', faculty_view.render_faculties_page, name='faculty'),  # Все факультеты
    path('admin/add/faculty/', faculty_view.render_add_faculty_page, name='add_faculty'),  # Добавить
    path('admin/edit/faculty/', faculty_view.render_edit_faculty_page, name='edit_faculty'),  # Редактировать
    path('admin/delete/faculty/', faculty_view.render_delete_faculty_page, name='delete_faculty'),  # Удалить

    # Страницы для аудиторий
    path('admin/auditory/', auditory_views.render_faculties_page, name='auditory'),  # Все аудитории
    path('admin/add/auditory/', auditory_views.render_add_faculty_page, name='add_auditory'),  # Добавить
    path('admin/edit/auditory/', auditory_views.render_edit_faculty_page, name='edit_auditory'),  # Редактировать
    path('admin/delete/auditory/', auditory_views.render_delete_faculty_page, name='delete_auditory'),  # Удалить

    # Страницы для групп
    path('admin/groups/', group_views.render_all_groups_page, name='groups'),  # Все группы
    path('admin/add/group/', group_views.render_add_group_page, name='add_groups'),  # Добавить
    path('admin/edit/group/', group_views.render_edit_group_page, name='edit_groups'),  # Редактировать
    path('admin/delete/group/', group_views.render_delete_group_page, name='delete_groups'),  # Удалить

    # Страницы для дисциплин
    path('admin/discipline/', discipline_views.render_all_disciplines_page, name='discipline'),  # Все дисциплины
    path('admin/add/discipline/', discipline_views.render_add_discipline_page, name='add_discipline'),  # Добавить
    # Редактировать
    path('admin/edit/discipline/', discipline_views.render_edit_discipline_page, name='edit_discipline'),
    # Удалить
    path('admin/delete/discipline/', discipline_views.render_delete_discipline_page, name='delete_discipline'),

    # Страницы для расписаний (очное)
    path('admin/add/full_time_schedule/', schedule_views.render_add_schedule_page, name='schedule'),  # Добавить
    # Редактировать
    path('admin/edit/full_time_schedule/', schedule_views.render_edit_schedule_page, name='edit_schedule'),
    # Импорт очного расписания: отдельные страницы для файлов ВО и СПО
    path('admin/import/full_time_schedule/vo/', schedule_views.render_import_schedule_page_vo,
         name='import_schedule_vo'),
    path('admin/import/full_time_schedule/spo/', schedule_views.render_import_schedule_page_spo,
         name='import_schedule_spo'),
    # Сохранение результатов мультифайлового импорта (JSON, вызывается со страницы импорта)
    path('admin/import/full_time_schedule/save/', schedule_views.save_imported_full_time_schedules,
         name='import_schedule_save'),
    # Старый адрес очного импорта ведёт на страницу ВО
    path('admin/import/full_time_schedule/', RedirectView.as_view(pattern_name='import_schedule_vo'),
         name='import_schedule'),  # Импорт
    # Удалить
    path('admin/delete/full_time_schedule/', schedule_views.render_delete_schedule_page, name='delete_schedule'),
    path('admin/edit/full_time_schedule/lesson/<int:slot_id>/',
         schedule_views.render_edit_schedule_page_for_chosen_lesson,
         name='for_edit_lesson'),  # Редактировать конкретный урок

    # Страницы для просмотра расписаний
    # По группам
    path('admin/schedule/group/', admin_views.render_schedule_by_group_page, name='check_schedule_group'),
    # По учителям
    path('admin/schedule/teacher/', admin_views.check_schedule_teachers, name='check_schedule_teachers'),
    path('admin/schedule/auditory/', admin_views.check_schedule_auditoriums,
         name='check_schedule_auditoriums'),  # По аудиториям

    # Страницы для расписаний (очно-заочные)
    path('admin/add/part_time_schedule/', part_time_schedule_views.render_add_page,
         name='add_part_time_schedule'),  # Добавить
    # path('admin/edit/part_time_schedule/', part_time_schedule_views.render_edit_page,
    #      name='edit_part_time_schedule'),  # Редактировать
    # Редактировать конкретный урок
    path('admin/edit/part_time_schedule/lesson/<int:slot_id>/',
         part_time_schedule_views.render_edit_page_for_chosen_lesson, name='edit_part_time_lesson'),
    path('admin/import/part_time_schedule/', part_time_schedule_views.render_import_page,
         name="import_part_time_schedule"),
    path('admin/delete/part_time_schedule/', part_time_schedule_views.render_edit_page,
         name='delete_part_time_schedule'),  # Удалить

    # Страницы для смешанных расписаний
    path('admin/add/mixed_schedule/', mixed_schedule_views.render_add_page,
         name='add_mixed_schedule'),  # Добавить
    path('admin/edit/mixed_schedule/', mixed_schedule_views.render_edit_page,
         name='edit_mixed_schedule'),  # Редактировать
    path('admin/edit/mixed_schedule/lesson/<int:slot_id>/', mixed_schedule_views.render_edit_page_for_chosen_lesson,
         name='edit_mixed_lesson'),  # Редактировать конкретный урок
    path('admin/import/mixed_schedule/', mixed_schedule_views.render_import_page, name='import_mixed_schedule'),
    # Импорт
    path('admin/delete/mixed_schedule/', mixed_schedule_views.render_delete_page, name='delete_mixed_schedule'),
    # Удалить
    path('export/', database_views.export_excel, name='export_excel'),

    # Правила отображения дисциплин в расписании преподавателя
    path('admin/teacher_rules/', teacher_rule_views.render_teacher_rules_page, name='teacher_rules'),

    # Настройка уведомлений (только для залогиненных)
    path('admin/notifications/', notification_views.render_notification_choice_page,
         name='notification_settings'),
    path('admin/notifications/teachers/', notification_views.render_notification_teachers_page,
         name='notification_teachers'),
    path('admin/notifications/auditoriums/', notification_views.render_notification_auditoriums_page,
         name='notification_auditoriums'),
    path('admin/notifications/teacher/<int:teacher_id>/',
         notification_views.render_notification_teacher_settings, name='notification_teacher_settings'),
    path('admin/notifications/auditorium/<int:auditorium_id>/',
         notification_views.render_notification_auditorium_settings,
         name='notification_auditorium_settings'),
    # JSON для шторки уведомлений (вне /admin/, поэтому закрыт @login_required)
    path('notifications/data/', notification_views.notifications_data, name='notifications_data'),

    # Резервные копии базы
    path('admin/backups/', backup_views.render_backups_page, name='backups'),
    path('admin/backups/download/<str:backup_name>/', backup_views.download_backup, name='download_backup'),

]

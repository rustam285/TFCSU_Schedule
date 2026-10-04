from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from .models import Lesson

        def touch_updated_at(sender, **kwargs):
            # импорт внутри обработчика: util тянет за собой forms, который на
            # этапе инициализации приложений выполняет запрос к БД (choices форм)
            from .services.util import touch_updated_at as handler

            handler(sender, **kwargs)

        # Даты «последнего изменения расписания» (глобальная и по каждой группе)
        # обновляются автоматически при любом создании/изменении/удалении занятия.
        # weak=False обязателен: connect() по умолчанию держит обработчик слабой
        # ссылкой — локальная функция из ready() собирается сборщиком мусора,
        # и сигнал молча перестаёт работать (из-за этого дата не обновлялась).
        post_save.connect(touch_updated_at, sender=Lesson, weak=False)
        post_delete.connect(touch_updated_at, sender=Lesson, weak=False)

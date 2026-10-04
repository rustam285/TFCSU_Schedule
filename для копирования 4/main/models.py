from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


class Auditorium(models.Model):
    building = models.IntegerField('Корпус', blank=True)
    number = models.IntegerField('Аудитория')  # трехзначное число


class Faculty(models.Model):
    code = models.CharField('Код', max_length=50, blank=True)
    title = models.TextField('Название')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Факультет'
        verbose_name_plural = 'Факультеты'


class Group(models.Model):
    class FormOfEducation(models.TextChoices):
        FULL_TIME = "о", _("Очная")
        PART_TIME = "з", _("Заочная")
        MIXED = "о-з", _("Очно-заочная")

    title = models.CharField('Название', max_length=50, blank=True)
    form_of_education = models.CharField('Форма обучения', max_length=50, choices=FormOfEducation)
    course = models.IntegerField('Курс')
    faculty = models.ForeignKey(Faculty, blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'


class Teacher(models.Model):
    name = models.CharField('ФИО', max_length=50)  # маска = "Фамилия И.О." или "[А-Я][а-я]* [А-Я]\.[А-Я]\."
    title = models.CharField('Ученое звание', max_length=100, blank=True)


class Discipline(models.Model):
    title = models.TextField('Название')
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, blank=True, null=True)
    teachers = models.ManyToManyField(Teacher, blank=True)


class Lesson(models.Model):
    class Number(models.Choices):
        FIRST = 1
        SECOND = 2
        SECOND_AND_HALF = 2.5
        THIRD = 3
        FOURTH = 4
        FIFTH = 5
        SIXTH = 6
        SEVENTH = 7
        EIGHTH = 8

    number = models.FloatField('Номер занятия', choices=Number)
    is_special = models.BooleanField('По специальному объявлению', default=False)
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE)
    format = models.CharField('Формат проведения', max_length=50, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    auditorium = models.ForeignKey(Auditorium, on_delete=models.SET_NULL, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Занятие'
        verbose_name_plural = 'Занятия'


class ConstantSchedule(models.Model):
    class WeekDay(models.TextChoices):
        MONDAY = "пн", _("Понедельник")
        TUESDAY = "вт", _("Вторник")
        WEDNESDAY = "ср", _("Среда")
        THURSDAY = "чт", _("Четверг")
        FRIDAY = "пт", _("Пятница")
        SATURDAY = "сб", _("Суббота")
        SUNDAY = "вс", _("Воскресенье")

    class WeekNumber(models.IntegerChoices):
        FIRST = 1
        SECOND = 2

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    week_day = models.CharField(max_length=2, choices=WeekDay)
    week_number = models.IntegerField('Номер недели', choices=WeekNumber)  # 1|2


class TemporarySchedule(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    date = models.DateField('Дата')


class SiteSetting(models.Model):
    """Простое key-value хранилище настроек сайта (например, дата последнего изменения расписания)."""

    key = models.CharField('Ключ', max_length=50, unique=True)
    value = models.TextField('Значение')

    def __str__(self):
        return f'{self.key} = {self.value}'

    class Meta:
        verbose_name = 'Настройка сайта'
        verbose_name_plural = 'Настройки сайта'


class TeacherDisciplineRule(models.Model):
    """Правило отображения дисциплин в расписании преподавателя.

    Пример: преподаватель фактически ведёт занятия по дисциплине, которая в базе
    числится за другим преподавателем, — такую дисциплину можно «показать дополнительно»
    в его расписании. Или наоборот — скрыть дисциплину из его расписания.

    По умолчанию правило действует только для залогиненных пользователей;
    галочка apply_for_guests распространяет его и на гостей.
    """

    class Mode(models.TextChoices):
        SHOW = "show", _("Показывать дополнительно")
        HIDE = "hide", _("Скрывать")

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name='Преподаватель')
    discipline = models.ForeignKey(Discipline, on_delete=models.CASCADE, verbose_name='Дисциплина')
    mode = models.CharField('Режим', max_length=4, choices=Mode, default=Mode.SHOW)
    apply_for_guests = models.BooleanField('Применять и для гостей', default=False)

    class Meta:
        verbose_name = 'Правило отображения дисциплины'
        verbose_name_plural = 'Правила отображения дисциплин'
        unique_together = ('teacher', 'discipline', 'mode')


class NotificationSubscription(models.Model):
    """Подписка залогиненного пользователя на уведомления о парах.

    Подписка либо на преподавателя, либо на аудиторию (второе поле — NULL).
    Режим mode задаёт, в какие дни показывать уведомления:
      default  — только если сегодня или завтра есть пары;
      dates    — только в конкретные даты (список в dates, JSON 'ГГГГ-ММ-ДД');
      weekdays — по дням недели с учётом чётности недели
                 (список в week_days, JSON '1-пн', '2-ср' — «неделя-день»).
    Уведомление в любом режиме появляется, только если в этот день есть хотя бы одна пара.
    """

    class Mode(models.TextChoices):
        DEFAULT = "default", _("По умолчанию (сегодня или завтра)")
        DATES = "dates", _("Конкретные даты")
        WEEKDAYS = "weekdays", _("Дни недели")

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, verbose_name='Преподаватель',
                                blank=True, null=True)
    auditorium = models.ForeignKey(Auditorium, on_delete=models.CASCADE, verbose_name='Аудитория',
                                   blank=True, null=True)
    mode = models.CharField('Режим', max_length=10, choices=Mode, default=Mode.DEFAULT)
    dates = models.TextField('Даты уведомлений', blank=True, default='[]')
    week_days = models.TextField('Дни недели уведомлений', blank=True, default='[]')

    class Meta:
        verbose_name = 'Подписка на уведомления'
        verbose_name_plural = 'Подписки на уведомления'

    def __str__(self):
        subject = f'преподаватель {self.teacher}' if self.teacher_id else \
            f'аудитория {self.auditorium.number if self.auditorium_id else "—"}'
        return f'{self.user.username}: {subject}'

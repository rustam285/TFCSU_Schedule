from django.contrib.auth.forms import AuthenticationForm
from django.forms import ModelForm, TextInput, MultipleChoiceField, NumberInput, PasswordInput, CharField
from django_select2.forms import Select2Widget

from .models import Group, Lesson, Teacher, Faculty, Auditorium, Discipline


class AddTeacherForm(ModelForm):
    class Meta:
        model = Teacher
        fields = ["name", "title"]
        widgets = {
            "name": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите Фамилию И.О. преподавателя'
            }),
            "title": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите должность преподавателя'
            }),
        }


class EditTeacherForm(ModelForm):
    class Meta:
        model = Teacher
        fields = ["id", "name", "title"]
        widgets = {
            "id": NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ID преподавателя, данные которого необходимо изменить'
            }),
            "name": TextInput(attrs={
                'class': 'form-control',
                'required': False,

                'placeholder': 'Введите Фамилию И.О. преподавателя'
            }),
            "title": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите должность преподавателя'
            }),
        }


class AuditoryForm(ModelForm):
    class Meta:
        model = Auditorium
        fields = ["building", "number"]
        widgets = {
            "building": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите номер корпуса'
            }),
            "number": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите номер аудитории'
            }),
        }


class EditAuditoryForm(ModelForm):
    class Meta:
        model = Auditorium
        fields = ["id", "building", "number"]
        widgets = {
            "id": NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ID аудитории, данные которой необходимо изменить'
            }),
            "building": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите номер аудитории'
            }),
            "number": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите номер корпуса'
            }),
        }


class FacultyForm(ModelForm):
    class Meta:
        model = Faculty
        fields = ["code", "title"]
        widgets = {
            "code": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите код факультета',
            }),
            "title": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Укажите название факультета'
            }),
        }


class EditFacultyForm(ModelForm):
    class Meta:
        model = Faculty
        fields = ["id", "code", "title"]
        widgets = {
            "id": NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ID факультета, данные которого необходимо изменить'
            }),
            "code": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите код факультета',
            }),
            "title": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Укажите название факультета'
            }),
        }


class GroupForm(ModelForm):
    class Meta:
        model = Group
        fields = ["title", "form_of_education", "course", "faculty"]
        widgets = {
            "title": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название группы',
                'required': 'true',
            }),
            "form_of_education": Select2Widget(attrs={
                'class': 'select2',
                'data-placeholder': 'Форма обучения',
                'style': 'width: 200px;',
            }),
            "course": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите курс',
            }),
            "faculty": Select2Widget(attrs={
                'class': 'select2',
                'data-placeholder': 'Выберите факультет',
                'style': 'width: 200px;',
            }),
        }


class EditGroupForm(ModelForm):
    class Meta:
        model = Group
        fields = ["id", "title", "form_of_education", "course", "faculty"]
        widgets = {
            "id": NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ID группы, данные которой необходимо изменить'
            }),
            "title": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название группы',
                'required': 'true',
            }),
            "form_of_education": Select2Widget(attrs={
                'class': 'select2',
                'data-placeholder': 'Форма обучения',
                'style': 'width: 200px;',
            }),
            "course": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите курс'
            }),
            "faculty": Select2Widget(attrs={
                'class': 'select2',
                'data-placeholder': 'Выберите факультет',
                'style': 'width: 200px;',
            }),
        }


class DisciplineForm(ModelForm):
    class Meta:
        model = Discipline
        fields = ["title", "faculty"]
        widgets = {
            "title": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название дисциплины'
            }),
            "faculty": Select2Widget(attrs={
                'class': 'select2',
                'data-placeholder': 'Выберите факультет',
                'style': 'width: 200px;',
            }),
        }


class EditDisciplineForm(ModelForm):
    class Meta:
        model = Discipline
        fields = ["id", "title", "faculty"]
        widgets = {
            "id": NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ID дисциплины, данные которой необходимо изменить'
            }),
            "title": TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название дисциплины'
            }),
            "faculty": Select2Widget(attrs={
                'class': 'select2',
                'data-placeholder': 'Выберите факультет',
                'style': 'width: 200px;',
            }),
        }


class LoginUserForm(AuthenticationForm):
    username = CharField(label='Логин', widget=TextInput(attrs={'class': 'form-control'}))
    password = CharField(label='Пароль', widget=PasswordInput(attrs={'class': 'form-control'}))


class LessonForm(ModelForm):
    week_day = [('пн', 'Понедельник'), ('вт', 'Вторник'), ('ср', 'Среда'), ('чт', 'Четверг'),
                ('пт', 'Пятница'), ('сб', 'Суббота'), ('вс', 'Воскресенье')]
    week_number = ["1", "2"]
    time = {1: "8:00-9:30",
            2: "9:40-11:10",
            2.5: "10:00",
            3: "11:20-12:50",
            4: "13:15-14:45",
            5: "15:00-16:30",
            6: "16:40-18:10",
            7: "18:20-19:50",
            8: "19:55-21:25"}

    day = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    NUMBER_OF_LESSON_CHOICES = {1: "1",
                                2: "2",
                                2.5: "ЭКЗ",
                                3: "3",
                                4: "4",
                                5: "5",
                                6: "6",
                                7: "7",
                                8: "8"}

    class Meta:
        model = Lesson
        fields = ['number', 'discipline', 'group', 'teacher', 'auditorium']

    number = MultipleChoiceField(choices=NUMBER_OF_LESSON_CHOICES)
    discipline = MultipleChoiceField(choices=Discipline.objects.values_list('title', flat=True))
    group = MultipleChoiceField(choices=Group.objects.values_list('title', flat=True))
    teacher = MultipleChoiceField(choices=Teacher.objects.values_list('name', flat=True))
    auditorium = MultipleChoiceField(choices=Auditorium.objects.values_list('number', flat=True))

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.contrib import messages

from main.forms import AddTeacherForm, EditTeacherForm
from main.services import teacher_service

PAGE_SIZE = 25


def get_teachers_page(request):
    """Список преподавателей с поиском (q) и пагинацией."""
    query = request.GET.get('q', '')
    teachers = teacher_service.get_all()
    if query:
        teachers = teachers.filter(name__icontains=query)
    page_obj = Paginator(teachers, PAGE_SIZE).get_page(request.GET.get('page'))
    return page_obj, query


def get_all_teachers():
    return {'teachers': teacher_service.get_all()}


def get_all_teachers_with_form(form):
    teachers = get_all_teachers()
    teachers['form'] = form
    return teachers


def check_form_and_save(form, request):
    if form.is_valid():
        form.save()
    else:
        messages.error(request, "Некорректные данные")


@login_required
def render_all_teachers_page(request):
    page_obj, query = get_teachers_page(request)
    return render(request, 'main/teacher/TeacherViewPage.html', {
        'teachers': page_obj,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def render_add_teacher_page(request):
    if request.method == 'GET':
        return render(request, 'main/teacher/TeacherAddPage.html', get_all_teachers_with_form(AddTeacherForm()))
    if request.method == 'POST':
        check_form_and_save(AddTeacherForm(request.POST), request)
        return redirect('add_teachers')


@login_required
def render_edit_teacher_page(request):
    if request.method == 'GET':
        page_obj, query = get_teachers_page(request)
        return render(request, 'main/teacher/TeacherEditPage.html', {
            'teachers': page_obj,
            'page_obj': page_obj,
            'query': query,
            'form': EditTeacherForm(),
            'chosen_id': request.GET.get('id'),
        })
    if request.method == 'POST':
        check_form_and_save(EditTeacherForm(request.POST, instance=teacher_service.get_by_pk(request.POST.get('id'))),
                            request)
        return redirect('edit_teachers')


@login_required
def render_delete_teacher_page(request):
    if request.method == 'GET':
        page_obj, query = get_teachers_page(request)
        return render(request, 'main/teacher/TeacherDeletePage.html', {
            'teachers': page_obj,
            'page_obj': page_obj,
            'query': query,
            'chosen_id': request.GET.get('id'),
        })
    if request.method == 'POST':
        teacher_id = request.POST.get('id')
        if teacher_id:
            teacher_service.delete_by_pk(teacher_id)
        else:
            messages.error(request, "Некорректные данные")
        return redirect('delete_teachers')

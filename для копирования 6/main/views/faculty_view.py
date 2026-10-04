from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect

from main.forms import FacultyForm, EditFacultyForm
from main.services import faculties_service, util

PAGE_SIZE = 25


def get_faculties_page(request):
    """Список факультетов с поиском (q, без учёта регистра и е/ё) и пагинацией."""
    query = request.GET.get('q', '')
    faculties = util.filter_by_query(list(faculties_service.get_all()), query,
                                     lambda f: f.title)
    page_obj = Paginator(faculties, PAGE_SIZE).get_page(request.GET.get('page'))
    return page_obj, query


def get_all_faculties():
    return {'faculties': faculties_service.get_all()}


def get_all_faculties_with_form(form):
    faculties = get_all_faculties()
    faculties['form'] = form
    return faculties


def check_form_and_save(form, request):
    if form.is_valid():
        form.save()
    else:
        messages.error(request, "Некорректные данные")


@login_required
def render_faculties_page(request):
    page_obj, query = get_faculties_page(request)
    return render(request, 'main/faculty/FacultyViewPage.html', {
        'faculties': page_obj,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def render_add_faculty_page(request):
    if request.method == 'GET':
        return render(request, 'main/faculty/FacultyAddPage.html', get_all_faculties_with_form(FacultyForm()))
    if request.method == 'POST':
        check_form_and_save(FacultyForm(request.POST), request)
        return redirect('add_faculty')


@login_required
def render_edit_faculty_page(request):
    if request.method == 'GET':
        page_obj, query = get_faculties_page(request)
        return render(request, 'main/faculty/FacultyEditPage.html', {
            'faculties': page_obj,
            'page_obj': page_obj,
            'query': query,
            'form': EditFacultyForm(),
            'chosen_id': request.GET.get('id'),
        })
    if request.method == 'POST':
        check_form_and_save(EditFacultyForm(request.POST, instance=faculties_service.get_by_pk(request.POST.get('id'))),
                            request)
        return redirect('edit_faculty')


@login_required
def render_delete_faculty_page(request):
    if request.method == 'GET':
        page_obj, query = get_faculties_page(request)
        return render(request, 'main/faculty/FacultyDeletePage.html', {
            'faculties': page_obj,
            'page_obj': page_obj,
            'query': query,
            'chosen_id': request.GET.get('id'),
        })
    if request.method == 'POST':
        faculties_service.delete_by_pk(request.POST.get('id'))
        return redirect('delete_faculty')

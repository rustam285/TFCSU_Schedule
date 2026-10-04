from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect

from main.forms import DisciplineForm, EditDisciplineForm
from main.services import discipline_service, util

PAGE_SIZE = 25


def get_disciplines_page(request):
    """Список дисциплин с поиском (q, без учёта регистра и е/ё) и пагинацией."""
    query = request.GET.get('q', '')
    disciplines = util.filter_by_query(list(discipline_service.get_all()), query,
                                       lambda d: d.title)
    page_obj = Paginator(disciplines, PAGE_SIZE).get_page(request.GET.get('page'))
    return page_obj, query


def get_all_disciplines():
    return {'disciplines': discipline_service.get_all()}


def get_all_disciplines_with_form(form):
    disciplines = get_all_disciplines()
    disciplines['form'] = form
    return disciplines


def check_form_and_save(form, request):
    if form.is_valid():
        form.save()
    else:
        messages.error(request, "Некорректные данные")


@login_required
def render_all_disciplines_page(request):
    page_obj, query = get_disciplines_page(request)
    return render(request, 'main/discipline/DisciplineViewPage.html', {
        'disciplines': page_obj,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def render_add_discipline_page(request):
    if request.method == 'GET':
        return render(request, 'main/discipline/DisciplineAddPage.html', get_all_disciplines_with_form(DisciplineForm()))
    if request.method == 'POST':
        check_form_and_save(DisciplineForm(request.POST), request)
        return redirect('add_discipline')


@login_required
def render_edit_discipline_page(request):
    if request.method == 'GET':
        page_obj, query = get_disciplines_page(request)
        return render(request, 'main/discipline/DisciplineEditPage.html', {
            'disciplines': page_obj,
            'page_obj': page_obj,
            'query': query,
            'form': EditDisciplineForm(),
            'chosen_id': request.GET.get('id'),
        })
    if request.method == 'POST':
        check_form_and_save(
            EditDisciplineForm(request.POST, instance=discipline_service.get_by_pk(request.POST.get('id'))),
            request)
        return redirect('edit_discipline')


@login_required
def render_delete_discipline_page(request):
    if request.method == 'GET':
        page_obj, query = get_disciplines_page(request)
        return render(request, 'main/discipline/DisciplineDeletePage.html', {
            'disciplines': page_obj,
            'page_obj': page_obj,
            'query': query,
            'chosen_id': request.GET.get('id'),
        })
    if request.method == 'POST':
        discipline_service.delete_by_pk(request.POST.get('id'))
        return redirect('delete_discipline')

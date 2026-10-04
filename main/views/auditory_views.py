from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect

from main.forms import EditAuditoryForm, AuditoryForm
from main.services import auditorium_service

PAGE_SIZE = 25


def get_auditories_page(request):
    """Список аудиторий с поиском (q) и пагинацией."""
    query = request.GET.get('q', '')
    auditories = auditorium_service.get_all()
    if query:
        auditories = auditories.filter(number__icontains=query)
    page_obj = Paginator(auditories, PAGE_SIZE).get_page(request.GET.get('page'))
    return page_obj, query


def get_all_auditories():
    return {'auditories': auditorium_service.get_all()}


def get_all_auditories_with_form(form):
    auditories = get_all_auditories()
    auditories['form'] = form
    return auditories


def check_form_and_save(form, request):
    if form.is_valid():
        form.save()
    else:
        messages.error(request, "Некорректные данные")


@login_required
def render_faculties_page(request):
    page_obj, query = get_auditories_page(request)
    return render(request, 'main/auditorium/AuditoriumViewPage.html', {
        'auditories': page_obj,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def render_add_faculty_page(request):
    if request.method == 'GET':
        return render(request, 'main/auditorium/AuditoriumAddPage.html', get_all_auditories_with_form(AuditoryForm()))
    if request.method == 'POST':
        check_form_and_save(AuditoryForm(request.POST), request)
        return redirect('add_auditory')


@login_required
def render_edit_faculty_page(request):
    if request.method == 'GET':
        page_obj, query = get_auditories_page(request)
        return render(request, 'main/auditorium/AuditoryEditPage.html', {
            'auditories': page_obj,
            'page_obj': page_obj,
            'query': query,
            'form': EditAuditoryForm(),
            'chosen_id': request.GET.get('id'),
        })
    if request.method == 'POST':
        check_form_and_save(
            EditAuditoryForm(request.POST, instance=auditorium_service.get_by_pk(request.POST.get('id'))),
            request)
        return redirect('edit_auditory')


@login_required
def render_delete_faculty_page(request):
    if request.method == 'GET':
        page_obj, query = get_auditories_page(request)
        return render(request, 'main/auditorium/AuditoriumDeletePage.html', {
            'auditories': page_obj,
            'page_obj': page_obj,
            'query': query,
            'chosen_id': request.GET.get('id'),
        })
    if request.method == 'POST':
        auditorium_service.delete_by_pk(request.POST.get('id'))
        return redirect('delete_auditory')

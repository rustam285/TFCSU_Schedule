from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect

from main.forms import GroupForm, EditGroupForm
from main.services import group_service, util

PAGE_SIZE = 25


def get_groups_page(request):
    """Список групп с поиском (q, без учёта регистра и е/ё) и пагинацией."""
    query = request.GET.get('q', '')
    groups = util.filter_by_query(list(group_service.get_all()), query, lambda g: g.title)
    page_obj = Paginator(groups, PAGE_SIZE).get_page(request.GET.get('page'))
    return page_obj, query


def get_all_groups():
    return {'groups': group_service.get_all()}


def get_all_groups_with_form(form):
    groups = get_all_groups()
    groups['form'] = form
    return groups


def check_form_and_save(form, request):
    if form.is_valid():
        form.save()
    else:
        errors = form.errors.as_data()
        for field, field_errors in errors.items():
            for error in field_errors:
                messages.error(request, f"Ошибка в поле '{field}': {error.message}")


@login_required
def render_all_groups_page(request):
    page_obj, query = get_groups_page(request)
    return render(request, 'main/group/GroupViewPage.html', {
        'groups': page_obj,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def render_add_group_page(request):
    if request.method == 'GET':
        return render(request, 'main/group/GroupAddPage.html', get_all_groups_with_form(GroupForm()))
    if request.method == 'POST':
        check_form_and_save(GroupForm(request.POST), request)
        return redirect('add_groups')


@login_required
def render_edit_group_page(request):
    if request.method == 'GET':
        page_obj, query = get_groups_page(request)
        return render(request, 'main/group/GroupEditPage.html', {
            'groups': page_obj,
            'page_obj': page_obj,
            'query': query,
            'form': EditGroupForm(),
            'chosen_id': request.GET.get('id'),
        })
    if request.method == 'POST':
        check_form_and_save(
            EditGroupForm(request.POST, instance=group_service.get_by_pk(request.POST.get('id'))),
            request)
        return redirect('edit_groups')


@login_required
def render_delete_group_page(request):
    if request.method == 'GET':
        page_obj, query = get_groups_page(request)
        return render(request, 'main/group/GroupDeletePage.html', {
            'groups': page_obj,
            'page_obj': page_obj,
            'query': query,
            'chosen_id': request.GET.get('id'),
        })
    if request.method == 'POST':
        group_service.delete_by_pk(request.POST.get('id'))
        return redirect('delete_groups')

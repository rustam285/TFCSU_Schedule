import os
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect

from main.backup import create_backup, get_backup_by_name, list_backups


@login_required
def render_backups_page(request):
    if request.method == "POST":
        if request.POST.get('create_backup'):
            try:
                path = create_backup(reason='manual')
                messages.success(request, f"Бэкап создан: {path.name}")
            except Exception as e:
                messages.error(request, f"Не удалось создать бэкап: {e}")
            return redirect('backups')
        if request.POST.get('delete_backup_name'):
            path = get_backup_by_name(request.POST.get('delete_backup_name'))
            if path:
                path.unlink()
                messages.success(request, f"Бэкап удалён: {path.name}")
            else:
                messages.error(request, "Бэкап не найден")
            return redirect('backups')

    backups = []
    for path in list_backups():
        stat = path.stat()
        backups.append({
            'name': path.name,
            'size_kb': round(stat.st_size / 1024, 1),
            'created': datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M'),
        })
    return render(request, 'main/BackupsPage.html', context={'backups': backups})


@login_required
def download_backup(request, backup_name):
    path = get_backup_by_name(backup_name)
    if not path:
        raise Http404("Бэкап не найден")
    # читаем в память: бэкапы маленькие (sqlite), а открытый FileResponse на Windows
    # блокировал бы файл при последующем удалении
    with open(path, 'rb') as f:
        data = f.read()
    response = HttpResponse(data, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{path.name}"'
    response['Content-Length'] = len(data)
    return response

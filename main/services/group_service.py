from main.models import Group


def get_all():
    return Group.objects.all().order_by('course').order_by('title')


def get_by_form_of_education(form):
    return Group.objects.filter(form_of_education=form)


def get_by_pk(pk):
    return Group.objects.get(pk=pk)


def delete_by_pk(pk):
    get_by_pk(pk).delete()


def is_exists_by_title(title):
    return Group.objects.filter(title=title).exists()


def get_by_title(title):
    return Group.objects.filter(title=title).first()

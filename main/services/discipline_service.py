from main.models import Discipline


def get_all():
    return Discipline.objects.all().order_by('title')


def get_by_pk(pk):
    return Discipline.objects.get(pk=pk)


def delete_by_pk(pk):
    get_by_pk(pk).delete()


def is_exists_by_title(title):
    return Discipline.objects.filter(title=title).exists()


def get_by_title(title):
    return Discipline.objects.filter(title=title).first()

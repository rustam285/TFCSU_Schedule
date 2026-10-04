from main.models import Faculty


def get_all():
    return Faculty.objects.all().order_by('title')


def get_by_pk(pk):
    return Faculty.objects.get(pk=pk)


def delete_by_pk(pk):
    get_by_pk(pk).delete()
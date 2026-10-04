from main.models import Auditorium


def get_all():
    return Auditorium.objects.all().order_by('number').order_by('building')


def get_by_pk(pk):
    return Auditorium.objects.get(pk=pk)


def delete_by_pk(pk):
    get_by_pk(pk).delete()


def is_exists_by_number(number):
    return Auditorium.objects.filter(number=number).exists()


def get_by_number(number):
    return Auditorium.objects.filter(number=number).first()

from main.models import Teacher


def get_all():
    return Teacher.objects.all().order_by('name')


def get_by_pk(pk):
    return Teacher.objects.get(pk=pk)


def delete_by_pk(teacher_id):
    get_by_pk(teacher_id).delete()


def is_exists_by_name(name):
    return Teacher.objects.filter(name=name).exists()


def get_by_name(name):
    return Teacher.objects.filter(name=name).first()

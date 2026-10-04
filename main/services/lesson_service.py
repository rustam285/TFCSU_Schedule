from main.models import Lesson


def get_by_pk(pk):
    return Lesson.objects.get(pk=pk)


def update(updated_lesson):
    updated_lesson.save()


def delete_by_pk(pk):
    lesson = get_by_pk(pk)
    lesson.delete()


def get_all():
    return Lesson.objects.all()

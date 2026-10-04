from django.core.management.base import BaseCommand

from main.backup import create_backup


class Command(BaseCommand):
    help = 'Создаёт резервную копию базы данных в папке backups/ (с ротацией старых копий)'

    def add_arguments(self, parser):
        parser.add_argument('--reason', default='',
                            help='Метка в имени файла (например: import, manual). Только буквы/цифры/дефис.')

    def handle(self, *args, **options):
        path = create_backup(reason=options['reason'])
        self.stdout.write(self.style.SUCCESS(f'Бэкап создан: {path.name}'))

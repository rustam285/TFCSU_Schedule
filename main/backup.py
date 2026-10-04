"""Резервное копирование базы данных (SQLite).

Используется sqlite3 backup API: копия согласована, даже если база открыта
другим процессом. Файлы складываются в backups/ у корня проекта,
старые сверх KEEP_LIMIT удаляются.
"""
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings

BACKUP_DIR_NAME = 'backups'
BACKUP_PREFIX = 'db_backup_'
BACKUP_SUFFIX = '.sqlite3'
# безопасное имя для подстановки метки: буквы/цифры/дефис
SAFE_REASON_RE = re.compile(r'^[A-Za-z0-9_-]{1,20}$')
KEEP_LIMIT = 30


def get_backup_dir() -> Path:
    backup_dir = Path(settings.BASE_DIR) / BACKUP_DIR_NAME
    backup_dir.mkdir(exist_ok=True)
    return backup_dir


def create_backup(reason: str = '') -> Path:
    """Создаёт резервную копию базы и возвращает путь к файлу."""
    if reason and not SAFE_REASON_RE.fullmatch(reason):
        raise ValueError(f'Недопустимая метка бэкапа: {reason!r}')

    db_path = Path(settings.DATABASES['default']['NAME'])
    if not db_path.exists():
        raise FileNotFoundError(f'Файл базы не найден: {db_path}')

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    suffix = f'_{reason}' if reason else ''
    target = get_backup_dir() / f'{BACKUP_PREFIX}{timestamp}{suffix}{BACKUP_SUFFIX}'

    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(target)
    try:
        with dst:
            src.backup(dst)
    finally:
        src.close()
        dst.close()

    rotate_backups()
    return target


def rotate_backups(keep: int = KEEP_LIMIT) -> list[Path]:
    """Оставляет последние `keep` бэкапов, остальные удаляет. Возвращает удалённые."""
    backups = sorted(list_backups())
    removed = []
    for old in backups[:-keep] if keep > 0 else backups:
        old.unlink()
        removed.append(old)
    return removed


def list_backups() -> list[Path]:
    """Список бэкапов от новых к старым."""
    return sorted(get_backup_dir().glob(f'{BACKUP_PREFIX}*{BACKUP_SUFFIX}'), reverse=True)


def get_backup_by_name(name: str) -> Path | None:
    """Бэкап по имени файла (только из списка существующих — защита от path traversal)."""
    for path in list_backups():
        if path.name == name:
            return path
    return None

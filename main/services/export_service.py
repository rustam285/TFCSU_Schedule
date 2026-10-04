"""Экспорт расписания в виде официальной сетки семестра: Excel, Word, PDF.

Вид: заголовок из двух строк (кого расписание + семестр) и сетка «дни × пары»,
где недели 1 и 2 идут рядом. Сетка строится по постоянному расписанию
(ConstantSchedule); разовые замены на конкретные даты (TemporarySchedule)
в бланк не включаются и остаются только на сайте.
"""
import datetime
import os
from urllib.parse import quote

from django.db.models import Q
from django.http import HttpResponse

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from main.forms import LessonForm
from main.models import ConstantSchedule
from main.services import teacher_rule_service

FONT_NAME = 'Times New Roman'
BASE_LESSON_ROWS = [1, 2, 3, 4, 5, 6]   # пары пн-пт, выводимые всегда; 7/8/ЭКЗ добавляются при наличии
WEEKEND_LESSON_ROWS = [1, 2, 3, 4, 5]   # сб (и вс, если есть занятия): 6-й пары нет; реальные занятия добавятся сами
LESSON_FIELDS = ('week_day', 'week_number', 'lesson__number', 'lesson__is_special',
                 'lesson__discipline__title', 'lesson__format', 'lesson__teacher__name',
                 'lesson__teacher__title', 'lesson__auditorium__number')


def get_semester_info(today=None):
    """(номер семестра, '2026-2027', '26-27') по текущей дате.

    Учебный год начинается 1 сентября: сентябрь-январь — 1 семестр,
    февраль-август — 2 семестр.
    """
    today = today or datetime.date.today()
    if today.month >= 9:
        start_year, semester = today.year, 1
    elif today.month == 1:
        start_year, semester = today.year - 1, 1
    else:
        start_year, semester = today.year - 1, 2
    return semester, f'{start_year}-{start_year + 1}', f'{start_year % 100:02d}-{(start_year + 1) % 100:02d}'


def _teacher_with_title(lesson):
    teacher = lesson['lesson__teacher__name']
    if teacher and lesson['lesson__teacher__title']:
        teacher += ', ' + lesson['lesson__teacher__title']
    return teacher


def _lesson_text(lesson, tail=''):
    """«*Дисциплина (формат), tail» — со звёздочкой спецобъявления и форматом."""
    text = ('*' if lesson['lesson__is_special'] else '') + lesson['lesson__discipline__title']
    if lesson['lesson__format']:
        text += f" ({lesson['lesson__format']})"
    if tail:
        text += ', ' + tail
    return text


def build_grid_for_group(group):
    """Сетка для группы: «Дисциплина (формат), преподаватель, звание» + аудитория."""
    lessons = ConstantSchedule.objects.filter(
        lesson__group=group).values(*LESSON_FIELDS).order_by('lesson__number')
    entries = [{'week_day': l['week_day'], 'week_number': l['week_number'],
                'number': l['lesson__number'],
                'text': _lesson_text(l, _teacher_with_title(l)),
                'aud': l['lesson__auditorium__number']} for l in lessons]
    subject = (f'Расписание группы {group.title} '
               f'({group.get_form_of_education_display().lower()} форма обучения)')
    return _assemble_grid(entries, f'{group.title}, {{week}} неделя', subject)


def build_grid_for_teacher(teacher, viewer_is_authenticated=False):
    """Сетка для преподавателя: одинаковые занятия разных групп объединяются в одну ячейку."""
    shown_ids, hidden_ids = teacher_rule_service.get_filtered_discipline_ids(
        teacher.pk, viewer_is_authenticated)
    query = ConstantSchedule.objects.filter(
        Q(lesson__teacher=teacher.pk) | Q(lesson__discipline__in=shown_ids or []))
    if hidden_ids:
        query = query.exclude(lesson__discipline__in=hidden_ids)
    lessons = query.values(*LESSON_FIELDS, 'lesson__group__title').order_by('lesson__number')
    merged = {}
    for l in lessons:
        key = (l['week_day'], l['week_number'], l['lesson__number'],
               l['lesson__discipline__title'], l['lesson__format'], l['lesson__auditorium__number'])
        merged.setdefault(key, {'lesson': l, 'groups': []})['groups'].append(l['lesson__group__title'])
    entries = [{'week_day': day, 'week_number': week, 'number': number,
                'text': _lesson_text(data['lesson'], ', '.join(sorted(data['groups']))),
                'aud': data['lesson']['lesson__auditorium__number']}
               for (day, week, number, *_), data in merged.items()]
    subject = f'Расписание преподавателя {teacher.name}'
    if teacher.title:
        subject += f', {teacher.title}'
    return _assemble_grid(entries, '{week} неделя', subject)


def build_grid_for_auditorium(auditorium):
    """Сетка для аудитории.

    Если в слоте у нескольких групп одна и та же дисциплина (и преподаватель) —
    одна строка «Дисциплина (формат), преподаватель — группы»; разные дисциплины
    выводятся отдельными строками. Колонки аудиторий не нужны.
    """
    lessons = ConstantSchedule.objects.filter(
        lesson__auditorium=auditorium).values(*LESSON_FIELDS, 'lesson__group__title'
                                              ).order_by('lesson__number')
    merged = {}
    for l in lessons:
        key = (l['week_day'], l['week_number'], l['lesson__number'],
               l['lesson__discipline__title'], l['lesson__format'],
               l['lesson__teacher__name'], l['lesson__teacher__title'])
        merged.setdefault(key, {'lesson': l, 'groups': []})['groups'].append(l['lesson__group__title'])
    entries = []
    for (day, week, number, *_), data in merged.items():
        l = data['lesson']
        teacher = _teacher_with_title(l)
        groups = ', '.join(sorted(data['groups']))
        tail = f"{teacher} — {groups}" if teacher else groups
        entries.append({'week_day': day, 'week_number': week, 'number': number,
                        'text': _lesson_text(l, tail), 'aud': None})
    return _assemble_grid(entries, '{week} неделя', f'Расписание аудитории {auditorium.number}',
                          with_auditorium_columns=False)


def _assemble_grid(entries, column_title_template, subject_title, with_auditorium_columns=True):
    """Собирает сетку «дни × пары» из списка занятий.

    Дни идут с понедельника; воскресенье выводится, только если в нём есть занятия.
    Строки дня — пары с 1 по максимум(базового списка, последняя занятая пара);
    у субботы и воскресенья базовый список короче (до 5-й пары).
    """
    lesson_form = LessonForm()
    by_day = {}
    for e in entries:
        by_day.setdefault(e['week_day'], {}).setdefault(e['week_number'], {}) \
            .setdefault(e['number'], []).append(e)

    days = []
    for day_key, day_label in lesson_form.week_day:
        if day_key == 'вс' and day_key not in by_day:
            continue
        day_map = by_day.get(day_key, {})
        base_rows = WEEKEND_LESSON_ROWS if day_key in ('сб', 'вс') else BASE_LESSON_ROWS
        numbers = sorted(set(day_map.get(1, {})) | set(day_map.get(2, {})) | set(base_rows))
        rows = []
        for number in numbers:
            cells = {}
            for week in (1, 2):
                in_slot = day_map.get(week, {}).get(number, [])
                if in_slot:
                    aud = ('\n'.join(str(l['aud']) for l in in_slot if l['aud'] is not None)
                           if with_auditorium_columns else None)
                    cells[week] = ('\n'.join(l['text'] for l in in_slot), aud)
                else:
                    cells[week] = (None, None)
            rows.append({'number': lesson_form.NUMBER_OF_LESSON_CHOICES[number],
                         'time': lesson_form.time[number], 1: cells[1], 2: cells[2]})
        days.append({'label': day_label, 'rows': rows})

    semester, full_year, short_year = get_semester_info()
    return {
        'days': days,
        'column_titles': {week: column_title_template.format(week=week) for week in (1, 2)},
        'title': [subject_title, f'{semester} семестр {full_year} учебного года'],
        'year_short': short_year,
        'with_auditorium_columns': with_auditorium_columns,
    }


def _file_name(title):
    name = title
    for ch in '\\/:*?"<>| ':
        name = name.replace(ch, '_')
    return name


def _attachment_response(content_type, extension, title):
    """HttpResponse с правильным Content-Disposition (кириллица в имени файла)."""
    response = HttpResponse(content_type=content_type)
    response['Content-Disposition'] = (
        f'attachment; filename="raspisanie{extension}"; '
        f"filename*=UTF-8''{quote(_file_name(title) + extension)}")
    return response


def _estimate_line_count(text, chars_per_line):
    return max(1, sum(max(1, -(-len(line) // chars_per_line)) for line in text.split('\n')))


def _header_labels(grid):
    if grid['with_auditorium_columns']:
        return ['д/н', '№', 'Время', grid['column_titles'][1], '№ ауд.',
                grid['column_titles'][2], '№ ауд.']
    return ['д/н', '№', 'Время', grid['column_titles'][1], grid['column_titles'][2]]


# --------------------------------------------------------------------------
# Excel (.xlsx)
# --------------------------------------------------------------------------

def build_xlsx_response(grid, file_title):
    ncols = 7 if grid['with_auditorium_columns'] else 5
    aud_columns = (5, 7) if grid['with_auditorium_columns'] else ()
    lesson_columns = (4, 6) if grid['with_auditorium_columns'] else (4, 5)
    lesson_width = 43.6 if grid['with_auditorium_columns'] else 43

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Расписание'
    widths = [4.5, 3.0, 11.0] + ([lesson_width, 4.2] * 2 if grid['with_auditorium_columns']
                                 else [lesson_width, lesson_width])
    for letter, width in zip('ABCDEFG'[:ncols], widths):
        sheet.column_dimensions[letter].width = width

    # Заголовок: две строки — кого расписание и семестр
    for offset, line in enumerate(grid['title']):
        row = 1 + offset
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
        cell = sheet.cell(row=row, column=1, value=line)
        cell.font = Font(name=FONT_NAME, size=12 if offset == 0 else 10, bold=offset == 0)
        cell.alignment = Alignment(horizontal='center')

    # Шапка таблицы
    header_row = len(grid['title']) + 1
    for column, header in enumerate(_header_labels(grid), start=1):
        sheet.cell(row=header_row, column=column, value=header)

    # Сетка: блок дня занимает len(rows) строк, название дня — вертикально в колонке A
    row_number = header_row + 1
    for day in grid['days']:
        first_row = row_number
        for slot in day['rows']:
            sheet.cell(row=row_number, column=2, value=slot['number'])
            sheet.cell(row=row_number, column=3, value=slot['time'])
            for week, lesson_column, aud_column in ((1, 4, 5), (2, 6, 7)):
                if not grid['with_auditorium_columns'] and week == 2:
                    lesson_column = 5
                text, aud = slot[week]
                if text:
                    sheet.cell(row=row_number, column=lesson_column, value=text)
                    if grid['with_auditorium_columns'] and aud:
                        sheet.cell(row=row_number, column=aud_column, value=aud)
            row_number += 1
        if row_number - 1 > first_row:
            sheet.merge_cells(start_row=first_row, start_column=1,
                              end_row=row_number - 1, end_column=1)
        sheet.cell(row=first_row, column=1, value=day['label'].lower())

    # Оформление: Times New Roman, выравнивание, границы (внешняя рамка толще внутренней)
    for row in sheet.iter_rows(min_row=header_row, max_row=row_number - 1, min_col=1, max_col=ncols):
        for cell in row:
            is_header_or_day = cell.row == header_row or cell.column == 1
            cell.font = Font(name=FONT_NAME, size=10 if is_header_or_day else 11,
                             bold=is_header_or_day)
            cell.border = Border(
                left=Side(style='medium' if cell.column == 1 else 'thin'),
                right=Side(style='medium' if cell.column == ncols else 'thin'),
                top=Side(style='medium' if cell.row == header_row else 'thin'),
                bottom=Side(style='medium' if cell.row == row_number - 1 else 'thin'))
            if cell.row == header_row:
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            elif cell.column == 1:
                cell.alignment = Alignment(horizontal='center', vertical='center', text_rotation=90)
            elif cell.column == 2:
                cell.alignment = Alignment(horizontal='center', vertical='center')
            elif cell.column == 3:
                cell.alignment = Alignment(horizontal='left', vertical='center')
            elif cell.column in aud_columns:
                cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            elif cell.column in lesson_columns:
                cell.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)

    # Высоты строк — по самому «высокому» занятию строки (Excel не растягивает сам)
    row_index = header_row + 1
    for day in grid['days']:
        for slot in day['rows']:
            lines = max((_estimate_line_count(slot[week][0], 40)
                         for week in (1, 2) if slot[week][0]), default=1)
            sheet.row_dimensions[row_index].height = max(15, lines * 13.5 + 2)
            row_index += 1

    response = _attachment_response(
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx', file_title)
    workbook.save(response)
    return response


# --------------------------------------------------------------------------
# Word (.docx) — книжная ориентация A4, таблица всегда на одной странице
# --------------------------------------------------------------------------

def _set_vertical_text(cell):
    """Вертикальный текст (снизу вверх) в ячейке таблицы Word."""
    direction = OxmlElement('w:textDirection')
    direction.set(qn('w:val'), 'btLr')
    cell._tc.get_or_add_tcPr().append(direction)


def _set_docx_cell_margins(table):
    """Убирает внутренние отступы ячеек — высотой таблицы управляем сами."""
    margins = OxmlElement('w:tblCellMar')
    for side in ('top', 'left', 'bottom', 'right'):
        element = OxmlElement(f'w:{side}')
        element.set(qn('w:w'), '20' if side in ('left', 'right') else '0')
        element.set(qn('w:type'), 'dxa')
        margins.append(element)
    table._tbl.tblPr.append(margins)


def _docx_cell(cell, text, bold=False, size=None):
    """Пишет текст в ячейку без интервалов между абзацами (иначе Word раздувает строки)."""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    if text is not None:
        run = paragraph.add_run(text)
        run.bold = bold
        if size is not None:
            run.font.size = Pt(size)
    return paragraph


def _set_docx_row_height(row, height_pt):
    """Фиксированная высота строки — таблица гарантированно не уедет на вторую страницу."""
    tr_height = OxmlElement('w:trHeight')
    tr_height.set(qn('w:val'), str(int(height_pt * 20)))  # twips
    tr_height.set(qn('w:hRule'), 'exact')
    row._tr.get_or_add_trPr().append(tr_height)


DOCX_COLUMN_WIDTHS = {7: [1.1, 0.8, 2.0, 6.6, 0.9, 6.6, 0.9],
                      5: [1.1, 0.8, 2.0, 7.5, 7.5]}

# Шрифт, при котором таблица гарантированно выше страницы; с него начинаем уменьшение
DOCX_MAX_TABLE_FONT = 9
DOCX_MIN_TABLE_FONT = 4.5


def _docx_fit_rows(grid, ncols, avail_height_pt):
    """Высоты строк под одну страницу и размер шрифта для них.

    Перебирает размер шрифта от большего к меньшему и оценивает высоту каждой
    строки по числу строк текста в ячейках (запас берётся с избытком). Высоты
    распределяются пропорционально и фиксируются — Word не сможет перенести
    таблицу на вторую страницу.
    """
    lesson_width_pt = DOCX_COLUMN_WIDTHS[ncols][3] * 28.35
    slots = [slot for day in grid['days'] for slot in day['rows']]
    heights, size = None, DOCX_MIN_TABLE_FONT
    for candidate in (9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5, 5, 4.5):
        chars_per_line = max(12, int(lesson_width_pt / (candidate * 0.55)))
        line_height = candidate * 1.35 + 1
        candidate_heights = [line_height]  # шапка
        for slot in slots:
            lines = 1
            for week in (1, 2):
                text, _ = slot[week]
                if not text:
                    continue
                cell_lines = sum(max(1, -(-len(part) // chars_per_line))
                                 for part in text.split('\n'))
                lines = max(lines, cell_lines)
            candidate_heights.append(lines * line_height)
        if sum(candidate_heights) <= avail_height_pt:
            size, heights = candidate, candidate_heights
            break
    if heights is None:  # даже 4.5 не влезает — всё равно фиксируем, пусть с обрезкой
        heights = candidate_heights
    # пропорционально растягиваем ровно на доступную высоту
    scale = avail_height_pt / sum(heights)
    min_height = size * 1.35 + 1
    return size, [max(min_height, h * scale) for h in heights]


def build_docx_response(grid, file_title):
    ncols = 7 if grid['with_auditorium_columns'] else 5
    document = Document()

    section = document.sections[0]
    section.page_width, section.page_height = Cm(21.0), Cm(29.7)
    section.left_margin = section.right_margin = Cm(1.0)
    section.top_margin = section.bottom_margin = Cm(1.0)

    for index, line in enumerate(grid['title']):
        paragraph = document.add_paragraph(line)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(2)
        for run in paragraph.runs:
            run.bold = index == 0
            run.font.size = Pt(13 if index == 0 else 11)

    table = document.add_table(rows=1, cols=ncols)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_docx_cell_margins(table)

    for cell, header in zip(table.rows[0].cells, _header_labels(grid)):
        _docx_cell(cell, header, bold=True, size=DOCX_MAX_TABLE_FONT)

    for day in grid['days']:
        rows = [table.add_row() for _ in day['rows']]
        for row, slot in zip(rows, day['rows']):
            _docx_cell(row.cells[1], slot['number'])
            _docx_cell(row.cells[2], slot['time'])
            for week, lesson_column, aud_column in ((1, 3, 4), (2, 5, 6)):
                if not grid['with_auditorium_columns'] and week == 2:
                    lesson_column = 4
                text, aud = slot[week]
                if text:
                    _docx_cell(row.cells[lesson_column], text)
                    if grid['with_auditorium_columns'] and aud:
                        _docx_cell(row.cells[aud_column], aud)
        day_cell = rows[0].cells[0]
        if len(rows) > 1:
            day_cell = day_cell.merge(rows[-1].cells[0])
        paragraph = day_cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(day['label'].lower())
        run.bold = True
        _set_vertical_text(day_cell)

    # Одна страница: подбираем шрифт, фиксируем высоты строк, применяем размер
    avail_height_pt = 29.7 * 28.35 - 2 * 1.0 * 28.35 - 45  # страница - поля - заголовок
    font_size, row_heights = _docx_fit_rows(grid, ncols, avail_height_pt)
    for run in [run for row in table.rows for cell in row.cells
                for paragraph in cell.paragraphs for run in paragraph.runs]:
        run.font.size = Pt(font_size)
    for row, height in zip(table.rows, row_heights):
        _set_docx_row_height(row, height)

    column_widths = [Cm(width) for width in DOCX_COLUMN_WIDTHS[ncols]]
    for row in table.rows:
        for index, cell in enumerate(row.cells):
            if index < ncols:
                cell.width = column_widths[index]

    response = _attachment_response(
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.docx', file_title)
    document.save(response)
    return response


# --------------------------------------------------------------------------
# PDF — книжная ориентация A4, таблица всегда на одной странице
# --------------------------------------------------------------------------

_font_registered = False


def _ensure_pdf_font():
    """Регистрирует шрифт с поддержкой кириллицы (Times New Roman, как в бланке)."""
    global _font_registered
    if _font_registered:
        return
    regular_candidates = [
        r'C:\Windows\Fonts\times.ttf',
        r'C:\Windows\Fonts\arial.ttf',
        r'C:\Windows\Fonts\tahoma.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    bold_candidates = [
        r'C:\Windows\Fonts\timesbd.ttf',
        r'C:\Windows\Fonts\arialbd.ttf',
        r'C:\Windows\Fonts\tahomabd.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    regular = next((path for path in regular_candidates if os.path.exists(path)), None)
    bold = next((path for path in bold_candidates if os.path.exists(path)), None)
    if not regular:
        raise RuntimeError(
            'Для экспорта в PDF не найден системный шрифт с поддержкой кириллицы. '
            'Искались: ' + ', '.join(regular_candidates))
    pdfmetrics.registerFont(TTFont('ExportFont', regular))
    pdfmetrics.registerFont(TTFont('ExportFont-Bold', bold or regular))
    _font_registered = True


class _FitToPageTable(Flowable):
    """Таблица, равномерно уменьшающаяся, чтобы занять ровно одну страницу.

    Аналог «вписать лист на страницу» в Excel: если таблица выше доступного
    места, она целиком масштабируется (текст, строки, рамки — пропорционально).
    """

    def __init__(self, table, avail_width, avail_height):
        super().__init__()
        self.table = table
        # Высоту считаем без ограничения: при включённом longTableOptimize
        # reportlab вычисляет объединения ячеек только до строки, покрывшей
        # availHeight, — а мы потом рисуем таблицу целиком.
        _, natural_height = table.wrap(avail_width, 10 ** 6)
        self.natural_width = float(sum(table._colWidths))
        self.scale = min(1.0, avail_height / natural_height)
        self.width = avail_width
        self.height = natural_height * self.scale

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        self.canv.saveState()
        self.canv.scale(self.scale, self.scale)
        x_offset = (self.width - self.natural_width * self.scale) / 2 / self.scale
        self.table.drawOn(self.canv, x_offset, 0)
        self.canv.restoreState()


class _VerticalText(Flowable):
    """Текст, повёрнутый на 90° (читается снизу вверх) — названия дней в колонке д/н."""

    def __init__(self, text, font='ExportFont-Bold', size=9):
        super().__init__()
        self.text, self.font, self.size = text, font, size
        self.box_width = size * 1.3
        self.box_height = pdfmetrics.stringWidth(text, font, size) + 2

    def wrap(self, availWidth, availHeight):
        return self.box_width, self.box_height

    def draw(self):
        self.canv.setFont(self.font, self.size)
        self.canv.rotate(90)
        self.canv.drawString(0, -self.size, self.text)


PDF_COLUMN_WIDTHS = {7: [0.8, 0.9, 2.1, 6.9, 0.9, 6.9, 0.9],
                     5: [0.8, 0.9, 2.1, 7.8, 7.8]}


def build_pdf_response(grid, file_title):
    _ensure_pdf_font()
    title_style = ParagraphStyle('TitleStyle', fontName='ExportFont-Bold', fontSize=13,
                                 leading=16, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle('SubtitleStyle', fontName='ExportFont', fontSize=11,
                                    leading=14, alignment=TA_CENTER)
    header_style = ParagraphStyle('HeaderStyle', fontName='ExportFont-Bold', fontSize=8.5,
                                  leading=10, alignment=TA_CENTER)
    cell_style = ParagraphStyle('CellStyle', fontName='ExportFont', fontSize=8.5, leading=10)
    center_style = ParagraphStyle('CenterStyle', fontName='ExportFont', fontSize=8.5,
                                  leading=10, alignment=TA_CENTER)

    def as_paragraph(text, style):
        return Paragraph(str(text).replace('\n', '<br/>'), style)

    pdf_rows = [[as_paragraph(header, header_style) for header in _header_labels(grid)]]
    spans = []
    for day in grid['days']:
        first_row = len(pdf_rows)
        for index, slot in enumerate(day['rows']):
            # колонка 0 — название дня вертикально (в верхней строке блока)
            row = [_VerticalText(day['label'].lower(), size=9) if index == 0 else '']
            row.append(as_paragraph(slot['number'], center_style))
            row.append(as_paragraph(slot['time'], center_style))
            for week in (1, 2):
                text, aud = slot[week]
                row.append(as_paragraph(text, cell_style) if text else '')
                if grid['with_auditorium_columns']:
                    row.append(as_paragraph(aud, center_style) if aud else '')
            pdf_rows.append(row)
        spans.append(('SPAN', (0, first_row), (0, len(pdf_rows) - 1)))

    ncols = 7 if grid['with_auditorium_columns'] else 5
    table_width = sum(PDF_COLUMN_WIDTHS[ncols]) * cm
    table = Table(pdf_rows, colWidths=[width * cm for width in PDF_COLUMN_WIDTHS[ncols]],
                  repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'ExportFont'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.6, colors.black),
        ('LINEABOVE', (0, 0), (-1, 0), 1.4, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1.4, colors.black),
        ('LINEBEFORE', (0, 0), (0, -1), 1.4, colors.black),
        ('LINEAFTER', (-1, 0), (-1, -1), 1.4, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ] + spans))

    # страница минус поля, заголовок и внутренние отступы фрейма (6pt сверху и снизу)
    table_avail_height = A4[1] - 2 * 0.8 * cm - 68
    story = [Paragraph(grid['title'][0], title_style),
             Paragraph(grid['title'][1], subtitle_style),
             Spacer(1, 10),
             _FitToPageTable(table, table_width, table_avail_height)]

    response = _attachment_response('application/pdf', '.pdf', file_title)
    document = SimpleDocTemplate(
        response, pagesize=A4,
        leftMargin=0.8 * cm, rightMargin=0.8 * cm, topMargin=0.8 * cm, bottomMargin=0.8 * cm,
        title=grid['title'][0])
    document.build(story)
    return response


# --------------------------------------------------------------------------
# Единая точка входа
# --------------------------------------------------------------------------

BUILDERS = {
    'xlsx': build_xlsx_response,
    'docx': build_docx_response,
    'pdf': build_pdf_response,
}


def export_schedule(grid, file_format, file_title):
    """Возвращает HttpResponse с файлом сетки расписания в выбранном формате."""
    builder = BUILDERS.get(file_format)
    if builder is None:
        raise ValueError(f'Неизвестный формат экспорта: {file_format}')
    return builder(grid, file_title)

import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List

from xlrd.sheet import Sheet

from app.service.model.LessonModel import LessonModel
from app.service.model.WeekScheduleModel import GroupsScheduleModel
from app.utill.constants import LESSON_FORMATS
from app.utill.enums.day_of_week import DayOfWeek


class AbstractParserService(ABC):
    @abstractmethod
    def check_and_save_column_names(self, sheet: Sheet):
        pass

    @abstractmethod
    def get_groups_name_list(self, sheet: Sheet) -> List[str]:
        pass

    @abstractmethod
    def get_groups_schedule(self, groups: List[str], sheet: Sheet) -> List[GroupsScheduleModel]:
        pass

    @staticmethod
    def get_merged_value(sheet: Sheet, row: int, col: int):
        for (rlo, rhi, clo, chi) in sheet.merged_cells:
            if rlo <= row < rhi and clo <= col < chi:
                return sheet.cell_value(rlo, clo)  # всегда верхняя левая
        return sheet.cell_value(row, col)

    def parse_week_schedule(self, current_row: int, lesson_title_column: int, lesson_number_column: int,
                            day_title_column: int, aud_title_column: int, sheet: Sheet):
        week_schedule = {}

        current_row = current_row
        week_day_cell_value = str(sheet.cell_value(current_row, day_title_column)).strip().lower()

        for col_enum in DayOfWeek:
            if col_enum.value.lower() == week_day_cell_value:
                current_day = col_enum.value

                lesson_list = []
                while True:
                    lesson = self.form_lesson_model(current_row, lesson_title_column,
                                                    aud_title_column,
                                                    lesson_number_column,
                                                    sheet)
                    if lesson: lesson_list.append(lesson)
                    current_row += 1
                    week_day_cell_value = str(sheet.cell_value(current_row, day_title_column))
                    if self.get_merged_value(sheet, current_row, day_title_column) != current_day:
                        break

                if lesson_list: week_schedule[current_day] = lesson_list
        return week_schedule

    def parse_day_schedule(self, current_row: int, lesson_title_column: int, lesson_number_column: int,
                           date_title_column: int, aud_title_column: int, sheet: Sheet):
        lessons = {}
        while True:
            lessons_list = []
            try:
                num = int(self.get_merged_value(sheet, current_row, aud_title_column))
                current_date = self.get_merged_value(sheet, current_row, date_title_column)
                ## По какой-то причине если добавленно именно датой - тогда возвращается float
                if isinstance(current_date, float):
                    dt = datetime(1899, 12, 30) + timedelta(days=current_date)
                    current_date = dt.strftime("%d.%m.%Y")
                lesson = self.form_lesson_model(current_row, lesson_title_column,
                                                aud_title_column,
                                                lesson_number_column,
                                                sheet)
                if lesson:
                    ##Продолжение костыля для парт тайма
                    if isinstance(lesson, list):
                        for lesson_obj in lesson:
                            lessons.setdefault(current_date, []).append(lesson_obj)
                    else:
                        lessons.setdefault(current_date, []).append(lesson)
                current_row += 1
            except (ValueError, TypeError) as e:
                break

        return lessons

    def form_lesson_model(self, lesson_number_row: int, lesson_title_column: int, aud_title_column: int,
                          lesson_number_title_column: int, sheet: Sheet):
        discipline_cell = self.get_merged_value(sheet, lesson_number_row, lesson_title_column).strip()
        if discipline_cell != "" and "День самостоятельной работы" not in discipline_cell:
            ctype = sheet.cell_type(lesson_number_row, lesson_number_title_column)
            value = sheet.cell_value(lesson_number_row, lesson_number_title_column)
            ##УВЫ, ЭКСЕЛЬ ВОЗВРАЩАЕТ 1,2 КАК ЧИСЛО, ПОЭТОМУ СМОТРИМ ЧТО Б ЕСЛИ ЭТО ЧИСЛО ТО
            ##ОНО БЫЛО ИНТОВЫМ, ИБО ЗАПИСИ 1,0 БЫТЬ НЕ ДОЛЖНО
            if ctype == 2 and value.is_integer():
                numbers = [str(int(value))]
            else:
                numbers = [x.strip() for x in str(value).replace(".", ",").split(",")]

            is_special = False
            if discipline_cell and discipline_cell[0] == "*":
                is_special = True
                discipline_cell = discipline_cell[:0] + discipline_cell[0 + 1:]
            discipline_cell = discipline_cell.split(",")
            teacher_name = discipline_cell[1].strip() if len(discipline_cell) > 1 else "-"
            lesson_model_format, discipline_title = self.extract_format_and_date_from_discipline(
                discipline_cell[0])
            ## Убираем код вначале если есть
            discipline_title = re.sub(r'^[A-ZА-ЯЁa-zа-яё\d]+(?:\.\d+)+\s+', '',
                                      discipline_title).replace("\r", "").replace("\n", "")

            aud_number_cell_value = self.get_merged_value(sheet, lesson_number_row, aud_title_column)
            auditorium_number = self.get_aud_number(aud_number_cell_value)
            if auditorium_number is None:
                ## Для СПО со смежной парой
                try:
                    next_aud_number_cell_value = self.get_merged_value(sheet, lesson_number_row, aud_title_column + 2)
                    auditorium_number = self.get_aud_number(next_aud_number_cell_value)
                except:
                    pass
            ##Костыль для пар через запятую в part-time
            if len(numbers) > 1:
                lessons = []
                for number in numbers:
                    lessons.append(LessonModel(number=int(number),
                                               is_special=is_special,
                                               discipline_title=discipline_title,
                                               format=lesson_model_format,
                                               teacher_name=teacher_name,
                                               auditorium_number=auditorium_number))
                return lessons

            number = int(sheet.cell_value(lesson_number_row, lesson_number_title_column))
            return LessonModel(number=number,
                               is_special=is_special,
                               discipline_title=discipline_title,
                               format=lesson_model_format,
                               teacher_name=teacher_name,
                               auditorium_number=auditorium_number)

    def get_aud_number(self, value):
        try:
            return int(float(value))
        except:
            return None

    @staticmethod
    def get_cell_value(cell: list, sheet: Sheet):
        return sheet.cell_value(cell[0], cell[1])

    @staticmethod
    def extract_format_and_date_from_discipline(discipline_title: str):
        lesson_model_format = ""
        # Нахожу все значения в скобках и ищу есть ли там формат. Если есть и он не последний,
        # то след элемент в списке - дата старта
        brackets_values = [m.strip() for m in re.findall(r"\(([^)]*)\)", discipline_title)]
        if brackets_values:
            n = min(2, len(brackets_values))
            for index, item in enumerate(reversed(brackets_values[-n:])):
                for lesson_format in LESSON_FORMATS:
                    if item == lesson_format:
                        if index == 1:
                            lesson_model_format = item + ", " + brackets_values[-1]
                            discipline_title = discipline_title.split('(')
                            discipline_title = '('.join(discipline_title[:-2]).strip()
                        else:
                            lesson_model_format = item
                            pattern = r"\((?:\s*(" + "|".join(
                                map(re.escape, LESSON_FORMATS)) + r")\s*)\)"
                            discipline_title = re.sub(pattern, "", discipline_title).strip()
        return lesson_model_format, discipline_title

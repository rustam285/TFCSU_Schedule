from typing import List

from fastapi.exceptions import RequestValidationError
from xlrd.sheet import Sheet

from app.service.implementation.abstract_parser_service import AbstractParserService
from app.service.model.LessonModel import LessonModel
from app.service.model.WeekScheduleModel import GroupsScheduleModel, WeeksScheduleModel
from app.utill.enums.day_of_week import DayOfWeek
from app.utill.enums.required_column_names import RequiredColumnNames


class HEParserService(AbstractParserService):
    def __init__(self):
        self.day_title_cell = None
        self.lesson_number_title_cell = None
        self.first_week_lessons_title_cell = None
        self.second_week_lessons_title_cell = None
        self.first_week_aud_title_cell = None
        self.second_week_aud_title_cell = None

    def check_and_save_column_names(self, sheet: Sheet):
        matches = {col_enum: [] for col_enum in RequiredColumnNames}

        for row in range(sheet.nrows):
            for col in range(sheet.ncols):
                cell_value = str(self.get_merged_value(sheet, row, col)).strip().lower()
                if isinstance(cell_value, str): cell_value = cell_value.replace('\n', '')
                for col_enum in RequiredColumnNames:
                    cmp = (col_enum.value.lower() in cell_value
                           if col_enum in (RequiredColumnNames.WEEK1, RequiredColumnNames.WEEK2)
                           else col_enum.value.lower() == cell_value)

                    if cmp:
                        matches[col_enum].append((row, col))
                        break

        missing = [col for col in RequiredColumnNames if not matches[col]]
        if missing:
            raise RequestValidationError(
                f"Не найдены обязательные заголовки Excel: {[col.value for col in missing]}"
            )

        aud_positions = matches[RequiredColumnNames.AUD]
        if len(aud_positions) != 2 or aud_positions[0][0] != aud_positions[1][0]:
            raise RequestValidationError(f"Ожидалось 2 колонки 'ауд.', найдено 1")

        self.day_title_cell = matches.get(RequiredColumnNames.DN)[0]
        self.lesson_number_title_cell = matches.get(RequiredColumnNames.NUMBER)[0]
        self.first_week_lessons_title_cell = matches.get(RequiredColumnNames.WEEK1)[0]
        self.second_week_lessons_title_cell = matches.get(RequiredColumnNames.WEEK2)[0]
        self.first_week_aud_title_cell = aud_positions[0]
        self.second_week_aud_title_cell = aud_positions[1]

    def get_groups_name_list(self, sheet: Sheet) -> List[str]:
        return [str(sheet.cell_value(self.first_week_lessons_title_cell[0],
                                     self.first_week_lessons_title_cell[1])).split(", ")[0]]

    def get_groups_schedule(self, groups: List[str], sheet: Sheet) -> List[GroupsScheduleModel]:
        first_week = self.parse_week_schedule(self.first_week_lessons_title_cell[0] + 1,
                                              self.first_week_lessons_title_cell[1], self.lesson_number_title_cell[1],
                                              self.day_title_cell[1], self.first_week_aud_title_cell[1], sheet)
        second_week = self.parse_week_schedule(self.second_week_lessons_title_cell[0] + 1,
                                               self.second_week_lessons_title_cell[1], self.lesson_number_title_cell[1],
                                               self.day_title_cell[1], self.second_week_aud_title_cell[1], sheet)

        return [GroupsScheduleModel(groups=groups, schedule=WeeksScheduleModel(first_week=first_week,
                                                                               second_week=second_week))]

from typing import List

from fastapi.exceptions import RequestValidationError
from xlrd.sheet import Sheet

from app.service.implementation.abstract_parser_service import AbstractParserService
from app.service.model.WeekScheduleModel import GroupsScheduleModel, WeeksScheduleModel, GroupsSchedulePTModel
from app.utill.enums.required_column_names import RequiredPartTimeColumnNames


class PTParserService(AbstractParserService):
    def __init__(self):
        self.date_title_cell = None
        self.lesson_number_title_cell = None
        self.lessons_title_cell = None
        self.aud_title_cell = None

    def check_and_save_column_names(self, sheet: Sheet):
        matches = {col_enum: [] for col_enum in RequiredPartTimeColumnNames}

        for row in range(sheet.nrows):
            for col in range(sheet.ncols):
                cell_value = str(self.get_merged_value(sheet, row, col)).strip().lower()
                if isinstance(cell_value, str): cell_value = cell_value.replace('\n', '')
                for col_enum in RequiredPartTimeColumnNames:
                    if col_enum.value.lower() == cell_value:
                        matches[col_enum].append((row, col))
                        break

        missing = [col for col in RequiredPartTimeColumnNames if not matches[col]]
        if missing:
            raise RequestValidationError(
                f"Не найдены обязательные заголовки Excel: {[col.value for col in missing]}"
            )

        self.date_title_cell = matches.get(RequiredPartTimeColumnNames.DATE)[-1]
        self.lesson_number_title_cell = matches.get(RequiredPartTimeColumnNames.NUMBER)[-1]
        self.aud_title_cell = matches.get(RequiredPartTimeColumnNames.AUD)[-1]
        self.lessons_title_cell = (self.aud_title_cell[0], self.aud_title_cell[1] - 1)

    def get_groups_name_list(self, sheet: Sheet) -> List[str]:
        return [self.get_merged_value(sheet, self.lessons_title_cell[0],
                                      self.lessons_title_cell[1]).split(", ")[0]]

    def get_groups_schedule(self, groups: List[str], sheet: Sheet) -> List[GroupsSchedulePTModel]:
        lessons = self.parse_day_schedule(self.lessons_title_cell[0] + 1,
                                          self.lessons_title_cell[1], self.lesson_number_title_cell[1],
                                          self.date_title_cell[1], self.aud_title_cell[1], sheet)

        return [GroupsSchedulePTModel(groups=groups, schedule=lessons)]

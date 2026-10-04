import re
from typing import List

from fastapi.exceptions import RequestValidationError
from xlrd.sheet import Sheet

from app.service.implementation.abstract_parser_service import AbstractParserService
from app.service.model.LessonModel import LessonModel
from app.service.model.WeekScheduleModel import GroupsScheduleModel, WeeksScheduleModel
from app.utill.enums.day_of_week import DayOfWeek
from app.utill.enums.required_column_names import RequiredSVEColumnNames


class SVEParserService(AbstractParserService):
    def __init__(self):
        self.first_groups_list = None
        self.second_groups_list = None
        self.first_week_day_title_cell = None
        self.first_week_lesson_number_cell = None
        self.first_week_first_group_lesson_title_cell = None
        self.first_week_first_group_lesson_aud_cell = None
        self.first_week_second_group_lesson_title_cell = None
        self.first_week_second_group_lesson_aud_cell = None

        self.second_week_day_title_cell = None
        self.second_week_lesson_number_cell = None
        self.second_week_first_group_lesson_title_cell = None
        self.second_week_first_group_lesson_aud_cell = None
        self.second_week_second_group_lesson_title_cell = None
        self.second_week_second_group_lesson_aud_cell = None


    ##Привет диспетчеру и спасибо за такую крутую валидацию.
    ##Проверить название предмета невозможно. Читай README
    def check_and_save_column_names(self, sheet: Sheet):
        matches = {col_enum: [] for col_enum in RequiredSVEColumnNames}

        for row in range(sheet.nrows):
            for col in range(sheet.ncols):
                cell_value = str(self.get_merged_value(sheet, row, col)).strip().lower()
                if isinstance(cell_value, str): cell_value = cell_value.replace('\n', '')
                for col_enum in RequiredSVEColumnNames:
                    cmp = (col_enum.value.lower() in cell_value
                           if col_enum in (RequiredSVEColumnNames.WEEK1, RequiredSVEColumnNames.WEEK2)
                           else col_enum.value.lower() == cell_value)

                    if cmp:
                        matches[col_enum].append((row, col))
                        break

        if not matches[RequiredSVEColumnNames.WEEK1] or not matches[RequiredSVEColumnNames.WEEK2]:
            raise RequestValidationError("Необходимо наличие надписей 1 неделя и 2 неделя")

        missing = []

        for req in RequiredSVEColumnNames:
            if req not in (RequiredSVEColumnNames.WEEK1, RequiredSVEColumnNames.WEEK2, RequiredSVEColumnNames.AUD):
                if not matches[req] or matches[req][0][0] != (matches[RequiredSVEColumnNames.WEEK1][0][0] + 1):
                    missing.append(req)

        if missing:
            raise RequestValidationError(
                f"Не найдены обязательные заголовки Excel для 1 недели: {[col.value for col in missing]}"
            )

        for req in RequiredSVEColumnNames:
            if req not in (RequiredSVEColumnNames.WEEK1, RequiredSVEColumnNames.WEEK2, RequiredSVEColumnNames.AUD):
                if len(matches[req]) < 2 or matches[req][1][0] != (
                        matches[RequiredSVEColumnNames.WEEK2][0][0] + 1):
                    missing.append(req)


        if missing:
            raise RequestValidationError(
                f"Не найдены обязательные заголовки Excel для 2 недели: {[col.value for col in missing]}"
            )

        aud_positions = matches[RequiredSVEColumnNames.AUD]

        if len(aud_positions) < 2 or aud_positions[0][0] != aud_positions[1][0]:
            raise RequestValidationError(f"Ожидалось 2 колонки '{RequiredSVEColumnNames.AUD.value}' на 1 неделе")

        if len(aud_positions) < 4 or aud_positions[2][0] != aud_positions[3][0]:
            raise RequestValidationError(f"Ожидалось 2 колонки  '{RequiredSVEColumnNames.AUD.value}' на 2 неделе")
        ##Все lesson_title поменять если гений на диспетчере поменяет расположение колонок
        self.first_week_day_title_cell = matches.get(RequiredSVEColumnNames.DN)[0]
        self.first_week_lesson_number_cell = matches.get(RequiredSVEColumnNames.NUMBER)[0]
        self.first_week_first_group_lesson_aud_cell = matches.get(RequiredSVEColumnNames.AUD)[0]
        self.first_week_first_group_lesson_title_cell = [self.first_week_first_group_lesson_aud_cell[0],
                                                         self.first_week_first_group_lesson_aud_cell[1] - 1]
        self.first_week_second_group_lesson_aud_cell = matches.get(RequiredSVEColumnNames.AUD)[1]
        self.first_week_second_group_lesson_title_cell = [self.first_week_second_group_lesson_aud_cell[0],
                                                          self.first_week_second_group_lesson_aud_cell[1] - 1]

        self.second_week_day_title_cell = matches.get(RequiredSVEColumnNames.DN)[1]
        self.second_week_lesson_number_cell = matches.get(RequiredSVEColumnNames.NUMBER)[1]
        self.second_week_first_group_lesson_aud_cell = matches.get(RequiredSVEColumnNames.AUD)[2]
        self.second_week_first_group_lesson_title_cell = [self.second_week_first_group_lesson_aud_cell[0],
                                                          self.second_week_first_group_lesson_aud_cell[1] - 1]
        self.second_week_second_group_lesson_aud_cell = matches.get(RequiredSVEColumnNames.AUD)[3]
        self.second_week_second_group_lesson_title_cell = [self.second_week_second_group_lesson_aud_cell[0],
                                                           self.second_week_second_group_lesson_aud_cell[1] - 1]

        if self.get_cell_value(self.first_week_first_group_lesson_title_cell, sheet) != self.get_cell_value(
                self.second_week_first_group_lesson_title_cell, sheet):
            raise RequestValidationError("Название первых групп на 1 и 2 неделе должно быть идентичным")

        if self.get_cell_value(self.first_week_second_group_lesson_title_cell, sheet) != self.get_cell_value(
                self.second_week_second_group_lesson_title_cell, sheet):
            raise RequestValidationError("Название вторых групп на 1 и 2 неделе должно быть идентичным")

    def get_groups_name_list(self, sheet: Sheet) -> List[str]:
        first_groups = str(sheet.cell_value(self.first_week_first_group_lesson_title_cell[0],
                                            self.first_week_first_group_lesson_title_cell[1])).replace(" ", "")
        second_groups = str(sheet.cell_value(self.first_week_second_group_lesson_title_cell[0],
                                             self.first_week_second_group_lesson_title_cell[1])).replace(" ", "")

        ##Приходится добавлять иначе каждый раз сравнивать - лень
        first_groups_list = self.get_groups_list_from_cell(first_groups)
        self.first_groups_list = first_groups_list
        second_groups_list = self.get_groups_list_from_cell(second_groups)
        self.second_groups_list = second_groups_list

        duplicates = set(first_groups_list) & set(second_groups_list)
        if duplicates:
            raise RequestValidationError(f"Замечено дублирование групп: {', '.join(duplicates)}")

        return first_groups_list + second_groups_list

    def get_groups_list_from_cell(self, groups: str) -> List[str]:
        groups_list = []
        matches = re.finditer(r'([А-Я]+)-(\d+(?:,\d+)*)', groups)
        for m in matches:
            group_name = m.group(1)
            numbers = m.group(2).split(',')
            for num in numbers:
                groups_list.append(f"{group_name}-{num}")

        return groups_list

    ## Очередной костыль, да-да знаю, группы не используются
    def get_groups_schedule(self, groups: List[str], sheet: Sheet) -> List[GroupsScheduleModel]:
        first_week_first_group = self.get_group_first_week_schedule(sheet, self.first_groups_list[0])
        second_week_first_group = self.get_group_second_week_schedule(sheet, self.first_groups_list[0])

        first_groups_model = GroupsScheduleModel(groups=self.first_groups_list,
                                                 schedule=WeeksScheduleModel(first_week=first_week_first_group,
                                                                             second_week=second_week_first_group))

        first_week_second_group = self.get_group_first_week_schedule(sheet, self.second_groups_list[0])
        second_week_second_group = self.get_group_second_week_schedule(sheet, self.second_groups_list[0])
        second_groups_model = GroupsScheduleModel(groups=self.second_groups_list,
                                                  schedule=WeeksScheduleModel(first_week=first_week_second_group,
                                                                              second_week=second_week_second_group))

        return [first_groups_model, second_groups_model]

    def get_group_first_week_schedule(self, sheet: Sheet, group: str) -> dict[DayOfWeek, list[LessonModel]]:
        lesson_title_cell, aud_column = (
            (self.first_week_first_group_lesson_title_cell, self.first_week_first_group_lesson_aud_cell[1])
            if group in self.first_groups_list
            else (self.first_week_second_group_lesson_title_cell, self.first_week_second_group_lesson_aud_cell[1])
            if group in self.second_groups_list
            else (None, None)
        )
        return self.parse_week_schedule(lesson_title_cell[0] + 1, lesson_title_cell[1],
                                        self.first_week_lesson_number_cell[1],
                                        self.first_week_day_title_cell[1],
                                        aud_column, sheet)

    def get_group_second_week_schedule(self, sheet: Sheet, group: str) -> dict[DayOfWeek, list[LessonModel]]:
        lesson_title_cell, aud_column = (
            (self.second_week_first_group_lesson_title_cell, self.second_week_first_group_lesson_aud_cell[1])
            if group in self.first_groups_list
            else (self.second_week_second_group_lesson_title_cell, self.second_week_second_group_lesson_aud_cell[1])
            if group in self.second_groups_list
            else (None, None)
        )

        return self.parse_week_schedule(lesson_title_cell[0] + 1, lesson_title_cell[1],
                                        self.second_week_lesson_number_cell[1],
                                        self.second_week_day_title_cell[1],
                                        aud_column, sheet)

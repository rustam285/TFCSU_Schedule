from typing import List

import xlrd
from fastapi import UploadFile

from app.service.implementation.abstract_parser_service import AbstractParserService
from app.service.implementation.part_time_parser_service import PTParserService
from app.service.implementation.he_parser_service import HEParserService
from app.service.implementation.sve_parser_service import SVEParserService
from app.service.model.WeekScheduleModel import GroupsScheduleModel
from app.utill.enums.education_form import EducationForm
from app.utill.enums.education_type import EducationType


class ParserService:
    def __init__(self, he_parser_service: HEParserService, sve_parser_service: SVEParserService,
                 pt_parser_service: PTParserService):
        self.sheet = None
        self.he_parser_service = he_parser_service
        self.sve_parser_service = sve_parser_service
        self.pt_parser_service = pt_parser_service

    def parse(self, education_form: EducationForm, education_type: EducationType,
              excel_table: UploadFile):
        if education_form == EducationForm.PART_TIME:
            return self.parse_part_time(self.pt_parser_service, excel_table)
        else:
            return self.parse_full_time_and_mixed(
                self.he_parser_service if education_type == EducationType.HE else self.sve_parser_service,
                excel_table)

    def parse_full_time_and_mixed(self, parser_service: AbstractParserService,
                                  excel_table: UploadFile) -> List[GroupsScheduleModel]:
        contents = excel_table.file.read()
        workbook = xlrd.open_workbook(file_contents=contents)
        self.sheet = workbook.sheet_by_index(0)

        parser_service.check_and_save_column_names(self.sheet)

        groups = parser_service.get_groups_name_list(self.sheet)

        result = parser_service.get_groups_schedule(groups, self.sheet)

        return result

    def parse_part_time(self, parser_service: AbstractParserService,
                        excel_table: UploadFile) -> List[GroupsScheduleModel]:
        contents = excel_table.file.read()
        workbook = xlrd.open_workbook(file_contents=contents)
        self.sheet = workbook.sheet_by_index(0)

        parser_service.check_and_save_column_names(self.sheet)

        groups = parser_service.get_groups_name_list(self.sheet)

        result = parser_service.get_groups_schedule(groups, self.sheet)

        return result

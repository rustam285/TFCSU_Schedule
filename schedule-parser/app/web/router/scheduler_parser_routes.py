from typing import Annotated

from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException

from app.service.implementation.parser_service import ParserService
from app.utill.enums.education_form import EducationForm
from app.utill.enums.education_type import EducationType
from app.web.dto.response.schedule_parsing_response_dto import ScheduleParsingResultResponseDto, GroupsScheduleDto, \
    GroupsSchedulePTDto
from dependencies import get_parser_service

schedule_parser_router = APIRouter(prefix="/schedule/parser", tags=["ScheduleParser"])


@schedule_parser_router.post("/schedule/parse",
                             response_model=ScheduleParsingResultResponseDto)
async def parse(
        parser_service: Annotated[ParserService, Depends(get_parser_service)],
        education_form: EducationForm = Form(...),
        education_type: EducationType = Form(...),
        excel_table: UploadFile = File(...)

):
    if excel_table.content_type != "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        raise HTTPException(400, detail="Invalid document type")
    dto_class = GroupsSchedulePTDto if education_form == EducationForm.PART_TIME else GroupsScheduleDto

    result = parser_service.parse(education_form, education_type, excel_table)
    return ScheduleParsingResultResponseDto(
        results=[dto_class.model_validate(model) for model in result],
        education_form=education_form,
        education_type=education_type
    )

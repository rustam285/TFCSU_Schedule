from typing import Optional, List

from pydantic import ConfigDict

from app.utill.enums.day_of_week import DayOfWeek
from app.utill.enums.education_form import EducationForm
from app.utill.enums.education_type import EducationType
from app.utill.project_base_model import ProjectBaseModel


class LessonResponseDto(ProjectBaseModel):
    number: int
    is_special: bool
    discipline_title: str
    format: Optional[str]
    teacher_name: Optional[str]
    auditorium_number: Optional[int]


class WeeksScheduleResponseDto(ProjectBaseModel):
    first_week: dict[DayOfWeek, list[LessonResponseDto]]
    second_week: dict[DayOfWeek, list[LessonResponseDto]]


class GroupsScheduleDto(ProjectBaseModel):
    groups: List[str]
    schedule: WeeksScheduleResponseDto


class GroupsSchedulePTDto(ProjectBaseModel):
    groups: List[str]
    schedule: dict[str, list[LessonResponseDto]]


class ScheduleParsingResultResponseDto(ProjectBaseModel):
    model_config = ConfigDict(extra="forbid")

    education_form: EducationForm
    education_type: EducationType

    results: list[GroupsScheduleDto | GroupsSchedulePTDto]

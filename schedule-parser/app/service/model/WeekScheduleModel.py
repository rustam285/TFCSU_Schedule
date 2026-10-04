from typing import List

from app.service.model.LessonModel import LessonModel
from app.utill.enums.day_of_week import DayOfWeek
from app.utill.project_base_model import ProjectBaseModel


class WeeksScheduleModel(ProjectBaseModel):
    first_week: dict[DayOfWeek, list[LessonModel]]
    second_week: dict[DayOfWeek, list[LessonModel]]

class GroupsScheduleModel(ProjectBaseModel):
    groups: List[str]
    schedule: WeeksScheduleModel

class GroupsSchedulePTModel(ProjectBaseModel):
    groups: List[str]
    schedule: dict[str, list[LessonModel]]
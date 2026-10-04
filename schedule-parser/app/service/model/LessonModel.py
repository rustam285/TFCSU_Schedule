from typing import Optional

from app.utill.project_base_model import ProjectBaseModel


class LessonModel(ProjectBaseModel):
    number: int
    is_special: bool
    discipline_title: str
    format: Optional[str]
    teacher_name: Optional[str]
    auditorium_number: Optional[int]

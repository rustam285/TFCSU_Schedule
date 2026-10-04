from pydantic import ConfigDict, BaseModel


class ProjectBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

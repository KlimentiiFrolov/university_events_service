from pydantic import BaseModel, ConfigDict


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TagListResponse(BaseModel):
    total: int
    items: list[TagResponse]

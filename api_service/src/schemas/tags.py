from pydantic import BaseModel


class TagResponse(BaseModel):
    id: int
    name: str


class TagListResponse(BaseModel):
    total: int
    items: list[TagResponse]

from pydantic import BaseModel, Field, computed_field


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, exclude=True)
    limit: int = Field(default=20, ge=1, le=100)

    @computed_field
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit

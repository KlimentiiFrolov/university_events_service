from pydantic import BaseModel, Field

from src.models.roles import RoleName


class CreateUserSchema(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    first_name: str = Field(min_length=1, max_length=127)
    second_name: str = Field(min_length=1, max_length=127)
    password_hash: str = Field(min_length=1, max_length=255)
    role: RoleName = RoleName.PARTICIPANT
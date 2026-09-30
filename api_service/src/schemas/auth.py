from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.models.roles import RoleName

BCRYPT_MAX_PASSWORD_BYTES = 72


def validate_password_length(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("Password must not exceed 72 bytes in UTF-8")

    return password


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str = Field(min_length=1, max_length=127)
    second_name: str = Field(min_length=1, max_length=127)

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        return validate_password_length(password)


class RegisterResponse(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    second_name: str
    role: RoleName


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        return validate_password_length(password)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
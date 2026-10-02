from fastapi import APIRouter, HTTPException, status

from dependencies import AuthServiceDep
from src.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from src.schemas.exceptions.domain import (
    ConflictError,
    InvalidCredentialsError,
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED,)
async def register(
    data: RegisterRequest,
    service: AuthServiceDep,
) -> RegisterResponse:
    try:
        user = await service.register(data)
    except ConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return RegisterResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        second_name=user.second_name,
        role=user.role.name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    data: LoginRequest,
    service: AuthServiceDep,
) -> TokenResponse:
    try:
        access_token = await service.login(data)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    return TokenResponse(
        access_token=access_token,
    )
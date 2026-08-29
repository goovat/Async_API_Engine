from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.authentication import get_current_user
from app.api.dependencies.database import get_db
from app.exceptions.authentication_errors import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from app.schemas.auth_login import LoginRequest
from app.schemas.auth_register import RegisterRequest
from app.schemas.token_response import TokenResponse
from app.services.authentication_service import AuthenticationService

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthenticationService(session)

    try:
        user = await service.register(
            email=payload.email,
            password=payload.password,
        )
        await session.commit()
    except UserAlreadyExistsError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        ) from exc

    return {
        "id": user.id,
        "email": user.email,
    }


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    service = AuthenticationService(session)

    try:
        access_token = await service.authenticate(
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenResponse(access_token=access_token)


@router.get("/me")
async def me(
    current_user=Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "email": current_user.email,
    }

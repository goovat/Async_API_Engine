from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.exceptions.authentication_errors import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from app.repositories.user_repository import UserRepository


class AuthenticationService:
    def __init__(self, session: AsyncSession) -> None:
        self.user_repository = UserRepository(session)
        self.password_hash = PasswordHash.recommended()

    def hash_password(self, password: str) -> str:
        return self.password_hash.hash(password)

    def verify_password(
        self,
        password: str,
        password_hash: str,
    ) -> bool:
        return self.password_hash.verify(password, password_hash)

    def create_access_token(self, user_id: int) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_expire_minutes
        )

        payload = {
            "sub": str(user_id),
            "exp": expires_at,
        }

        return jwt.encode(
            payload,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    async def register(
        self,
        email: str,
        password: str,
    ):
        existing_user = await self.user_repository.get_by_email(email)

        if existing_user is not None:
            raise UserAlreadyExistsError

        password_hash = self.hash_password(password)

        return await self.user_repository.create(
            email=email,
            password_hash=password_hash,
        )

    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> str:
        user = await self.user_repository.get_by_email(email)

        if user is None:
            raise InvalidCredentialsError

        if not self.verify_password(
            password,
            user.password_hash,
        ):
            raise InvalidCredentialsError

        return self.create_access_token(user.id)

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_key import IdempotencyKey
from app.repositories.idempotency_repository import IdempotencyRepository


class IdempotencyService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = IdempotencyRepository(session)

    async def get_or_create(
        self,
        user_id: int,
        key: str,
    ) -> tuple[IdempotencyKey, bool]:
        existing = await self.repository.get(
            user_id=user_id,
            key=key,
        )

        if existing is not None:
            return existing, False

        record = await self.repository.create(
            user_id=user_id,
            key=key,
        )

        return record, True

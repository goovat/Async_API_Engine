from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency_key import IdempotencyKey


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self,
        user_id: int,
        key: str,
    ) -> IdempotencyKey | None:
        result = await self.session.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.user_id == user_id,
                IdempotencyKey.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: int,
        key: str,
    ) -> IdempotencyKey:
        record = IdempotencyKey(
            user_id=user_id,
            key=key,
        )
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def attach_job(
        self,
        record: IdempotencyKey,
        job_id: int,
    ) -> IdempotencyKey:
        record.job_id = job_id
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def store_response(
        self,
        record: IdempotencyKey,
        response_body: str,
    ) -> IdempotencyKey:
        record.response_body = response_body
        await self.session.flush()
        await self.session.refresh(record)
        return record

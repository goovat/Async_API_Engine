from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.job_repository import JobRepository


class JobStatusService:
    def __init__(self, session: AsyncSession) -> None:
        self.job_repository = JobRepository(session)

    async def get_status(
        self,
        job_id: int,
        user_id: int,
    ):
        return await self.job_repository.get_by_id_for_user(
            job_id=job_id,
            user_id=user_id,
        )

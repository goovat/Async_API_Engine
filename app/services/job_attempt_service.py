from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.job_errors import JobNotFoundError
from app.repositories.job_attempt_repository import JobAttemptRepository
from app.repositories.job_repository import JobRepository


class JobAttemptService:
    def __init__(self, session: AsyncSession) -> None:
        self.job_repository = JobRepository(session)
        self.job_attempt_repository = JobAttemptRepository(session)

    async def get_attempts(
        self,
        job_id: int,
        user_id: int,
    ):
        job = await self.job_repository.get_by_id_for_user(
            job_id=job_id,
            user_id=user_id,
        )

        if job is None:
            raise JobNotFoundError

        return await self.job_attempt_repository.get_all_for_job(
            job_id=job_id,
        )

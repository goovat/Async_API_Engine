from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, job_id: int) -> Job | None:
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_for_user(
        self,
        job_id: int,
        user_id: int,
    ) -> Job | None:
        result = await self.session.execute(
            select(Job).where(
                Job.id == job_id,
                Job.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: int,
        job_type: str,
        payload: str,
    ) -> Job:
        job = Job(
            user_id=user_id,
            job_type=job_type,
            payload=payload,
            status="pending",
        )

        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)

        return job

    async def update_status(
        self,
        job: Job,
        status: str,
    ) -> Job:
        job.status = status

        await self.session.flush()
        await self.session.refresh(job)

        return job

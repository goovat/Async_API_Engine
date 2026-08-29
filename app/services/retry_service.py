from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.job_errors import JobNotFoundError
from app.models.job import Job
from app.repositories.job_attempt_repository import JobAttemptRepository
from app.repositories.job_repository import JobRepository
from app.workers.queue import JobQueue


class RetryService:
    def __init__(
        self,
        session: AsyncSession,
        queue: JobQueue | None = None,
    ) -> None:
        self.job_repository = JobRepository(session)
        self.job_attempt_repository = JobAttemptRepository(session)
        self.queue = queue or JobQueue()

    async def retry_job(
        self,
        job_id: int,
        user_id: int,
    ) -> Job:
        job = await self.job_repository.get_by_id_for_user(
            job_id=job_id,
            user_id=user_id,
        )

        if job is None:
            raise JobNotFoundError

        if job.status != "failed":
            raise ValueError(
                "Only failed jobs can be retried"
            )

        latest_attempt = (
            await self.job_attempt_repository.get_latest_for_job(
                job_id=job.id,
            )
        )

        if (
            latest_attempt is not None
            and latest_attempt.attempt_number >= 3
        ):
            raise ValueError(
                "Maximum retry attempts reached"
            )

        await self.job_repository.update_status(
            job=job,
            status="pending",
        )

        await self.queue.enqueue(job.id)

        return job

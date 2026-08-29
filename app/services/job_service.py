from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.job_repository import JobRepository
from app.services.idempotency_service import IdempotencyService
from app.workers.queue import JobQueue


class JobService:
    def __init__(
        self,
        session: AsyncSession,
        queue: JobQueue | None = None,
    ) -> None:
        self.job_repository = JobRepository(session)
        self.idempotency_service = IdempotencyService(session)
        self.queue = queue or JobQueue()

    async def create_job(
        self,
        user_id: int,
        job_type: str,
        payload: str,
        idempotency_key: str | None = None,
    ):
        if idempotency_key is not None:
            record, created = await self.idempotency_service.get_or_create(
                user_id=user_id,
                key=idempotency_key,
            )

            if not created:
                if record.job_id is None:
                    raise RuntimeError(
                        "Idempotency record exists without an attached job."
                    )

                job = await self.job_repository.get_by_id_for_user(
                    job_id=record.job_id,
                    user_id=user_id,
                )

                if job is None:
                    raise RuntimeError(
                        "Idempotency record references a missing job."
                    )

                return job

        job = await self.job_repository.create(
            user_id=user_id,
            job_type=job_type,
            payload=payload,
        )

        if idempotency_key is not None:
            await self.idempotency_service.repository.attach_job(
                record,
                job.id,
            )

        await self.queue.enqueue(job.id)

        return job

    async def get_job(
        self,
        job_id: int,
        user_id: int,
    ):
        return await self.job_repository.get_by_id_for_user(
            job_id=job_id,
            user_id=user_id,
        )

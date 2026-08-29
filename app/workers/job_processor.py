from sqlalchemy.ext.asyncio import AsyncSession

from app.observability.logging import get_logger
from app.repositories.job_attempt_repository import JobAttemptRepository
from app.repositories.job_repository import JobRepository


logger = get_logger("job_processor")


class JobProcessor:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.job_repository = JobRepository(session)
        self.job_attempt_repository = JobAttemptRepository(session)

    async def process(self, job_id: int) -> None:
        job = await self.job_repository.get_by_id_for_update(job_id)

        if job is None:
            logger.info(
                "job_not_found job_id=%s",
                job_id,
            )
            return

        if job.status != "pending":
            logger.info(
                "job_skipped job_id=%s status=%s",
                job.id,
                job.status,
            )
            return

        latest_attempt = (
            await self.job_attempt_repository.get_latest_for_job(
                job_id=job.id,
            )
        )

        attempt_number = (
            latest_attempt.attempt_number + 1
            if latest_attempt is not None
            else 1
        )

        attempt = await self.job_attempt_repository.create(
            job_id=job.id,
            attempt_number=attempt_number,
            status="processing",
        )

        logger.info(
            "job_attempt_started job_id=%s attempt_number=%s",
            job.id,
            attempt_number,
        )

        await self.job_repository.update_status(
            job=job,
            status="processing",
        )

        try:
            await self._execute(job.job_type, job.payload)

        except Exception as exc:
            await self.job_attempt_repository.update_status(
                attempt=attempt,
                status="failed",
                error_message=str(exc),
            )

            await self.job_repository.update_status(
                job=job,
                status="failed",
            )

            await self.session.commit()

            logger.error(
                "job_failed job_id=%s attempt_number=%s error=%s",
                job.id,
                attempt_number,
                str(exc),
            )

            return

        await self.job_attempt_repository.update_status(
            attempt=attempt,
            status="completed",
        )

        await self.job_repository.update_status(
            job=job,
            status="completed",
        )

        await self.session.commit()

        logger.info(
            "job_completed job_id=%s attempt_number=%s",
            job.id,
            attempt_number,
        )

    async def _execute(
        self,
        job_type: str,
        payload: str,
    ) -> None:
        if job_type != "example":
            raise ValueError(
                f"Unsupported job type: {job_type}"
            )

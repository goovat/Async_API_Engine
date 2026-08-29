from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_attempt import JobAttempt


class JobAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest_for_job(
        self,
        job_id: int,
    ) -> JobAttempt | None:
        result = await self.session.execute(
            select(JobAttempt)
            .where(JobAttempt.job_id == job_id)
            .order_by(desc(JobAttempt.attempt_number))
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def create(
        self,
        job_id: int,
        attempt_number: int,
        status: str,
    ) -> JobAttempt:
        attempt = JobAttempt(
            job_id=job_id,
            attempt_number=attempt_number,
            status=status,
        )

        self.session.add(attempt)
        await self.session.flush()
        await self.session.refresh(attempt)

        return attempt

    async def update_status(
        self,
        attempt: JobAttempt,
        status: str,
        error_message: str | None = None,
    ) -> JobAttempt:
        attempt.status = status
        attempt.error_message = error_message

        if status in {"completed", "failed"}:
            attempt.finished_at = datetime.now(timezone.utc)

        await self.session.flush()
        await self.session.refresh(attempt)

        return attempt

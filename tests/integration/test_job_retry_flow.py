import uuid

import pytest
from sqlalchemy import func, select

from app.database.session import AsyncSessionLocal
from app.models.job import Job
from app.models.job_attempt import JobAttempt
from app.services.authentication_service import AuthenticationService
from app.services.job_service import JobService
from app.services.retry_service import RetryService
from app.workers.queue import JobQueue
from app.workers.job_processor import JobProcessor


class RecordingQueue(JobQueue):
    def __init__(self) -> None:
        self.enqueued: list[int] = []

    async def enqueue(self, job_id: int) -> None:
        self.enqueued.append(job_id)


@pytest.mark.asyncio
async def test_failed_job_can_be_retried_and_completed():
    email = f"retry-flow-{uuid.uuid4().hex}@example.com"
    password = "test-password-123"

    async with AsyncSessionLocal() as session:
        auth_service = AuthenticationService(session)

        user = await auth_service.register(
            email=email,
            password=password,
        )

        await session.commit()
        user_id = user.id

    queue = RecordingQueue()

    async with AsyncSessionLocal() as session:
        service = JobService(
            session,
            queue=queue,
        )

        job = await service.create_job(
            user_id=user_id,
            job_type="example",
            payload='{"retry": true}',
        )

        await session.commit()
        job_id = job.id

    assert queue.enqueued == [job_id]

    async with AsyncSessionLocal() as session:
        processor = JobProcessor(session)

        async def failing_execute(
            job_type: str,
            payload: str,
        ) -> None:
            raise RuntimeError("temporary failure")

        processor._execute = failing_execute

        await processor.process(job_id)

    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)

        assert job is not None
        assert job.status == "failed"

        attempt_count = await session.scalar(
            select(func.count())
            .select_from(JobAttempt)
            .where(JobAttempt.job_id == job_id)
        )

        failed_count = await session.scalar(
            select(func.count())
            .select_from(JobAttempt)
            .where(
                JobAttempt.job_id == job_id,
                JobAttempt.status == "failed",
            )
        )

        failed_attempt = await session.scalar(
            select(JobAttempt)
            .where(JobAttempt.job_id == job_id)
        )

    assert attempt_count == 1
    assert failed_count == 1
    assert failed_attempt is not None
    assert failed_attempt.error_message == "temporary failure"

    retry_queue = RecordingQueue()

    async with AsyncSessionLocal() as session:
        retry_service = RetryService(
            session,
            queue=retry_queue,
        )

        retried_job = await retry_service.retry_job(
            job_id=job_id,
            user_id=user_id,
        )

        await session.commit()

        assert retried_job.status == "pending"

    assert retry_queue.enqueued == [job_id]

    async with AsyncSessionLocal() as session:
        processor = JobProcessor(session)

        async def successful_execute(
            job_type: str,
            payload: str,
        ) -> None:
            return None

        processor._execute = successful_execute

        await processor.process(job_id)

    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)

        assert job is not None
        assert job.status == "completed"

        attempt_count = await session.scalar(
            select(func.count())
            .select_from(JobAttempt)
            .where(JobAttempt.job_id == job_id)
        )

        completed_count = await session.scalar(
            select(func.count())
            .select_from(JobAttempt)
            .where(
                JobAttempt.job_id == job_id,
                JobAttempt.status == "completed",
            )
        )

        failed_count = await session.scalar(
            select(func.count())
            .select_from(JobAttempt)
            .where(
                JobAttempt.job_id == job_id,
                JobAttempt.status == "failed",
            )
        )

    assert attempt_count == 2
    assert completed_count == 1
    assert failed_count == 1

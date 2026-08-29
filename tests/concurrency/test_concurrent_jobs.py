import asyncio
import uuid

import pytest
from sqlalchemy import func, select

from app.database.session import AsyncSessionLocal
from app.models.idempotency_key import IdempotencyKey
from app.models.job import Job
from app.models.user import User
from app.services.authentication_service import AuthenticationService
from app.services.job_service import JobService
from app.workers.queue import JobQueue


class RecordingQueue(JobQueue):
    def __init__(self) -> None:
        self.enqueued: list[int] = []
        self._lock = asyncio.Lock()

    async def enqueue(self, job_id: int) -> None:
        async with self._lock:
            self.enqueued.append(job_id)


@pytest.mark.asyncio
async def test_concurrent_same_idempotency_key_creates_one_job():
    email = f"concurrent-{uuid.uuid4().hex}@example.com"
    password = "test-password-123"

    async with AsyncSessionLocal() as session:
        service = AuthenticationService(session)

        user = await service.register(
            email=email,
            password=password,
        )

        await session.commit()
        user_id = user.id

    queue = RecordingQueue()
    idempotency_key = f"concurrent-job-{uuid.uuid4().hex}"

    async def create_job():
        async with AsyncSessionLocal() as session:
            service = JobService(
                session,
                queue=queue,
            )

            job = await service.create_job(
                user_id=user_id,
                job_type="example",
                payload='{"concurrent": true}',
                idempotency_key=idempotency_key,
            )

            await session.commit()

            return job.id

    job_ids = await asyncio.gather(
        create_job(),
        create_job(),
    )

    assert job_ids[0] == job_ids[1]

    async with AsyncSessionLocal() as session:
        job_count = await session.scalar(
            select(func.count())
            .select_from(Job)
            .where(
                Job.user_id == user_id,
                Job.id == job_ids[0],
            )
        )

        key_count = await session.scalar(
            select(func.count())
            .select_from(IdempotencyKey)
            .where(
                IdempotencyKey.user_id == user_id,
                IdempotencyKey.key == idempotency_key,
            )
        )

    assert job_count == 1
    assert key_count == 1
    assert queue.enqueued == [job_ids[0]]

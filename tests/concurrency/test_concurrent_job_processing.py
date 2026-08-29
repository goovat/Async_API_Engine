import asyncio
import uuid

import pytest
from sqlalchemy import func, select

from app.database.session import AsyncSessionLocal
from app.models.job import Job
from app.models.job_attempt import JobAttempt
from app.models.user import User
from app.services.authentication_service import AuthenticationService
from app.services.job_service import JobService
from app.workers.job_processor import JobProcessor
from app.workers.queue import JobQueue


class RecordingQueue(JobQueue):
    def __init__(self) -> None:
        self.enqueued: list[int] = []

    async def enqueue(self, job_id: int) -> None:
        self.enqueued.append(job_id)


@pytest.mark.asyncio
async def test_concurrent_processors_execute_same_job_only_once():
    email = f"processor-concurrency-{uuid.uuid4().hex}@example.com"
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
            payload='{"concurrent": true}',
        )

        await session.commit()
        job_id = job.id

    first_started = asyncio.Event()
    release_first = asyncio.Event()
    executions = 0

    async def first_execute(
        job_type: str,
        payload: str,
    ) -> None:
        nonlocal executions

        executions += 1
        first_started.set()

        await release_first.wait()

    async def second_execute(
        job_type: str,
        payload: str,
    ) -> None:
        nonlocal executions

        executions += 1

    async with AsyncSessionLocal() as session1:
        processor1 = JobProcessor(session1)
        processor1._execute = first_execute

        first_task = asyncio.create_task(
            processor1.process(job_id)
        )

        await asyncio.wait_for(
            first_started.wait(),
            timeout=5,
        )

        async with AsyncSessionLocal() as session2:
            processor2 = JobProcessor(session2)
            processor2._execute = second_execute

            second_task = asyncio.create_task(
                processor2.process(job_id)
            )

            await asyncio.sleep(0.2)

            assert not second_task.done(), (
                "Second processor completed while the first "
                "processor still owned the job."
            )

            release_first.set()

            await asyncio.wait_for(
                first_task,
                timeout=5,
            )

            await asyncio.wait_for(
                second_task,
                timeout=5,
            )

    async with AsyncSessionLocal() as session:
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

        result = await session.scalar(
            select(Job.status).where(Job.id == job_id)
        )

    assert executions == 1
    assert attempt_count == 1
    assert completed_count == 1
    assert result == "completed"

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.job_service import JobService


@pytest.mark.asyncio
async def test_create_job_enqueues_created_job():
    session = MagicMock()
    queue = MagicMock()
    queue.enqueue = AsyncMock()

    service = JobService(session, queue=queue)

    job = MagicMock()
    job.id = 123

    service.job_repository.create = AsyncMock(
        return_value=job,
    )

    result = await service.create_job(
        user_id=1,
        job_type="example",
        payload="{}",
    )

    assert result is job

    service.job_repository.create.assert_awaited_once_with(
        user_id=1,
        job_type="example",
        payload="{}",
    )

    queue.enqueue.assert_awaited_once_with(123)


@pytest.mark.asyncio
async def test_get_job_uses_user_scoped_repository_lookup():
    session = MagicMock()

    service = JobService(session)

    job = MagicMock()

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=job,
    )

    result = await service.get_job(
        job_id=123,
        user_id=7,
    )

    assert result is job

    service.job_repository.get_by_id_for_user.assert_awaited_once_with(
        job_id=123,
        user_id=7,
    )

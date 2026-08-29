from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions.job_errors import JobNotFoundError
from app.services.retry_service import RetryService


@pytest.mark.asyncio
async def test_retry_missing_job_raises_not_found():
    session = MagicMock()

    service = RetryService(session)

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=None,
    )

    with pytest.raises(JobNotFoundError):
        await service.retry_job(
            job_id=999,
            user_id=1,
        )


@pytest.mark.asyncio
async def test_retry_requeues_job():
    session = MagicMock()
    queue = MagicMock()
    queue.enqueue = AsyncMock()

    service = RetryService(session, queue=queue)

    job = MagicMock()
    job.id = 10

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=job,
    )
    service.job_repository.update_status = AsyncMock()
    service.job_attempt_repository.create = AsyncMock()

    result = await service.retry_job(
        job_id=10,
        user_id=1,
    )

    assert result is job

    service.job_repository.update_status.assert_awaited_once_with(
        job=job,
        status="pending",
    )

    queue.enqueue.assert_awaited_once_with(10)


@pytest.mark.asyncio
async def test_retry_requeues_existing_job_without_creating_attempt():
    session = MagicMock()
    queue = MagicMock()
    queue.enqueue = AsyncMock()

    service = RetryService(session, queue=queue)

    job = MagicMock()
    job.id = 10

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=job,
    )
    service.job_repository.update_status = AsyncMock()
    service.job_attempt_repository.create = AsyncMock()

    result = await service.retry_job(
        job_id=10,
        user_id=1,
    )

    assert result is job

    queue.enqueue.assert_awaited_once_with(10)
    service.job_attempt_repository.create.assert_not_called()

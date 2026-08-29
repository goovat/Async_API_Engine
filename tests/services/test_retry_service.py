from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions.job_errors import (
    JobNotFoundError,
    JobNotRetryableError,
    MaxRetryAttemptsError,
)
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
    job.status = "failed"

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=job,
    )
    service.job_repository.update_status = AsyncMock()
    service.job_attempt_repository.get_latest_for_job = AsyncMock(
        return_value=None,
    )
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
    job.status = "failed"

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=job,
    )
    service.job_repository.update_status = AsyncMock()
    service.job_attempt_repository.get_latest_for_job = AsyncMock(
        return_value=None,
    )
    service.job_attempt_repository.create = AsyncMock()

    result = await service.retry_job(
        job_id=10,
        user_id=1,
    )

    assert result is job

    queue.enqueue.assert_awaited_once_with(10)
    service.job_attempt_repository.create.assert_not_called()

@pytest.mark.asyncio
async def test_retry_failed_job_requeues_it():
    session = MagicMock()
    queue = MagicMock()
    queue.enqueue = AsyncMock()

    service = RetryService(session, queue=queue)

    job = MagicMock()
    job.id = 10
    job.status = "failed"

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=job,
    )
    service.job_repository.update_status = AsyncMock()
    service.job_attempt_repository.get_latest_for_job = AsyncMock(
        return_value=None,
    )

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
async def test_retry_processing_job_is_rejected():
    session = MagicMock()
    queue = MagicMock()
    queue.enqueue = AsyncMock()

    service = RetryService(session, queue=queue)

    job = MagicMock()
    job.id = 10
    job.status = "processing"

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=job,
    )
    service.job_repository.update_status = AsyncMock()

    with pytest.raises(
        JobNotRetryableError,
        match="Only failed jobs can be retried",
    ):
        await service.retry_job(
            job_id=10,
            user_id=1,
        )

    service.job_repository.update_status.assert_not_awaited()
    queue.enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_completed_job_is_rejected():
    session = MagicMock()
    queue = MagicMock()
    queue.enqueue = AsyncMock()

    service = RetryService(session, queue=queue)

    job = MagicMock()
    job.id = 10
    job.status = "completed"

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=job,
    )
    service.job_repository.update_status = AsyncMock()

    with pytest.raises(
        JobNotRetryableError,
        match="Only failed jobs can be retried",
    ):
        await service.retry_job(
            job_id=10,
            user_id=1,
        )

    service.job_repository.update_status.assert_not_awaited()
    queue.enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_is_allowed_when_attempt_count_is_below_limit():
    session = MagicMock()
    queue = MagicMock()
    queue.enqueue = AsyncMock()

    service = RetryService(session, queue=queue)

    job = MagicMock()
    job.id = 10
    job.status = "failed"

    latest_attempt = MagicMock()
    latest_attempt.attempt_number = 2

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=job,
    )
    service.job_attempt_repository.get_latest_for_job = AsyncMock(
        return_value=latest_attempt,
    )
    service.job_repository.update_status = AsyncMock()

    result = await service.retry_job(
        job_id=10,
        user_id=1,
    )

    assert result is job

    service.job_attempt_repository.get_latest_for_job.assert_awaited_once_with(
        job_id=10,
    )
    service.job_repository.update_status.assert_awaited_once_with(
        job=job,
        status="pending",
    )
    queue.enqueue.assert_awaited_once_with(10)


@pytest.mark.asyncio
async def test_retry_is_rejected_when_max_attempts_reached():
    session = MagicMock()
    queue = MagicMock()
    queue.enqueue = AsyncMock()

    service = RetryService(session, queue=queue)

    job = MagicMock()
    job.id = 10
    job.status = "failed"

    latest_attempt = MagicMock()
    latest_attempt.attempt_number = 3

    service.job_repository.get_by_id_for_user = AsyncMock(
        return_value=job,
    )
    service.job_attempt_repository.get_latest_for_job = AsyncMock(
        return_value=latest_attempt,
    )
    service.job_repository.update_status = AsyncMock()

    with pytest.raises(
        MaxRetryAttemptsError,
        match="Maximum retry attempts reached",
    ):
        await service.retry_job(
            job_id=10,
            user_id=1,
        )

    service.job_repository.update_status.assert_not_awaited()
    queue.enqueue.assert_not_awaited()

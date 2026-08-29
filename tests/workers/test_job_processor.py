from unittest.mock import AsyncMock, MagicMock

import pytest

from app.workers.job_processor import JobProcessor


@pytest.mark.asyncio
async def test_missing_job_is_ignored():
    session = MagicMock()
    processor = JobProcessor(session)

    processor.job_repository.get_by_id = AsyncMock(
        return_value=None,
    )

    await processor.process(999)

    processor.job_repository.get_by_id.assert_awaited_once_with(999)


@pytest.mark.asyncio
async def test_successful_job_is_completed():
    session = MagicMock()
    processor = JobProcessor(session)

    job = MagicMock()
    job.id = 10
    job.job_type = "example"
    job.payload = '{"hello": "world"}'
    job.status = "pending"

    attempt = MagicMock()
    attempt.attempt_number = 1

    processor.job_repository.get_by_id = AsyncMock(
        return_value=job,
    )
    processor.job_attempt_repository.get_latest_for_job = AsyncMock(
        return_value=None,
    )
    processor.job_attempt_repository.create = AsyncMock(
        return_value=attempt,
    )
    processor.job_attempt_repository.update_status = AsyncMock()
    processor.job_repository.update_status = AsyncMock()
    session.commit = AsyncMock()

    await processor.process(10)

    processor.job_attempt_repository.create.assert_awaited_once_with(
        job_id=10,
        attempt_number=1,
        status="processing",
    )

    assert (
        processor.job_attempt_repository.update_status.await_args_list[0]
        .kwargs["status"]
        == "completed"
    )

    assert (
        processor.job_repository.update_status.await_args_list[-1]
        .kwargs["status"]
        == "completed"
    )

    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unsupported_job_type_fails_job():
    session = MagicMock()
    processor = JobProcessor(session)

    job = MagicMock()
    job.id = 20
    job.job_type = "unsupported"
    job.payload = "{}"
    job.status = "pending"

    attempt = MagicMock()

    processor.job_repository.get_by_id = AsyncMock(
        return_value=job,
    )
    processor.job_attempt_repository.get_latest_for_job = AsyncMock(
        return_value=None,
    )
    processor.job_attempt_repository.create = AsyncMock(
        return_value=attempt,
    )
    processor.job_attempt_repository.update_status = AsyncMock()
    processor.job_repository.update_status = AsyncMock()
    session.commit = AsyncMock()

    await processor.process(20)

    processor.job_attempt_repository.update_status.assert_awaited_once_with(
        attempt=attempt,
        status="failed",
        error_message="Unsupported job type: unsupported",
    )

    processor.job_repository.update_status.assert_any_await(
        job=job,
        status="failed",
    )

    session.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_processing_already_processing_job_is_skipped():
    session = MagicMock()
    processor = JobProcessor(session)

    job = MagicMock()
    job.id = 30
    job.job_type = "example"
    job.payload = '{"hello": "world"}'
    job.status = "processing"

    processor.job_repository.get_by_id = AsyncMock(
        return_value=job,
    )
    processor.job_attempt_repository.get_latest_for_job = AsyncMock(
        return_value=MagicMock(attempt_number=1),
    )
    processor.job_attempt_repository.create = AsyncMock()
    processor.job_repository.update_status = AsyncMock()
    session.commit = AsyncMock()

    await processor.process(30)

    processor.job_attempt_repository.create.assert_not_awaited()
    processor.job_repository.update_status.assert_not_awaited()
    session.commit.assert_not_awaited()


from unittest.mock import AsyncMock, MagicMock

import pytest

from app.observability.metrics import (
    JOBS_PROCESSED_TOTAL,
    JOB_ATTEMPTS_TOTAL,
)
from app.workers.job_processor import JobProcessor


def counter_value(counter, **labels):
    return counter.labels(**labels)._value.get()


@pytest.mark.asyncio
async def test_successful_job_increments_success_metrics():
    session = MagicMock()
    processor = JobProcessor(session)

    job = MagicMock()
    job.id = 101
    job.job_type = "example"
    job.payload = "{}"
    job.status = "pending"

    attempt = MagicMock()
    attempt.attempt_number = 1

    processor.job_repository.get_by_id_for_update = AsyncMock(
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

    attempts_before = counter_value(
        JOB_ATTEMPTS_TOTAL,
        status="started",
    )
    completed_attempts_before = counter_value(
        JOB_ATTEMPTS_TOTAL,
        status="completed",
    )
    completed_jobs_before = counter_value(
        JOBS_PROCESSED_TOTAL,
        status="completed",
    )

    await processor.process(101)

    assert (
        counter_value(JOB_ATTEMPTS_TOTAL, status="started")
        == attempts_before + 1
    )
    assert (
        counter_value(JOB_ATTEMPTS_TOTAL, status="completed")
        == completed_attempts_before + 1
    )
    assert (
        counter_value(JOBS_PROCESSED_TOTAL, status="completed")
        == completed_jobs_before + 1
    )


@pytest.mark.asyncio
async def test_failed_job_increments_failure_metrics():
    session = MagicMock()
    processor = JobProcessor(session)

    job = MagicMock()
    job.id = 102
    job.job_type = "unsupported"
    job.payload = "{}"
    job.status = "pending"

    attempt = MagicMock()
    attempt.attempt_number = 1

    processor.job_repository.get_by_id_for_update = AsyncMock(
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

    attempts_before = counter_value(
        JOB_ATTEMPTS_TOTAL,
        status="started",
    )
    failed_attempts_before = counter_value(
        JOB_ATTEMPTS_TOTAL,
        status="failed",
    )
    failed_jobs_before = counter_value(
        JOBS_PROCESSED_TOTAL,
        status="failed",
    )

    await processor.process(102)

    assert (
        counter_value(JOB_ATTEMPTS_TOTAL, status="started")
        == attempts_before + 1
    )
    assert (
        counter_value(JOB_ATTEMPTS_TOTAL, status="failed")
        == failed_attempts_before + 1
    )
    assert (
        counter_value(JOBS_PROCESSED_TOTAL, status="failed")
        == failed_jobs_before + 1
    )

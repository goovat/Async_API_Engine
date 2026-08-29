from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from app.workers.worker import Worker


def metric_value(name: str, labels: dict[str, str] | None = None) -> float:
    value = REGISTRY.get_sample_value(name, labels or {})
    return value or 0.0


@pytest.mark.asyncio
async def test_worker_completed_job_records_metric():
    queue = MagicMock()
    queue.dequeue = AsyncMock(return_value=123)

    session = MagicMock()

    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.workers.worker.AsyncSessionLocal",
        return_value=session_context,
    ), patch(
        "app.workers.worker.JobProcessor",
    ) as processor_class:
        processor = processor_class.return_value
        processor.process = AsyncMock()

        before = metric_value(
            "asyncapi_worker_jobs_total",
            {"status": "completed"},
        )

        worker = Worker(queue)

        result = await worker.process_next()

        after = metric_value(
            "asyncapi_worker_jobs_total",
            {"status": "completed"},
        )

    assert result is True
    assert after == before + 1


@pytest.mark.asyncio
async def test_worker_failed_job_records_metric():
    queue = MagicMock()
    queue.dequeue = AsyncMock(return_value=789)
    queue.enqueue = AsyncMock()

    session = MagicMock()

    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.workers.worker.AsyncSessionLocal",
        return_value=session_context,
    ), patch(
        "app.workers.worker.JobProcessor",
    ) as processor_class:
        processor = processor_class.return_value
        processor.process = AsyncMock(
            side_effect=RuntimeError("temporary processing failure"),
        )

        before = metric_value(
            "asyncapi_worker_jobs_total",
            {"status": "failed"},
        )

        worker = Worker(queue)

        with pytest.raises(
            RuntimeError,
            match="temporary processing failure",
        ):
            await worker.process_next()

        after = metric_value(
            "asyncapi_worker_jobs_total",
            {"status": "failed"},
        )

    assert after == before + 1


@pytest.mark.asyncio
async def test_worker_completed_job_records_duration():
    queue = MagicMock()
    queue.dequeue = AsyncMock(return_value=456)

    session = MagicMock()

    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(return_value=session)
    session_context.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.workers.worker.AsyncSessionLocal",
        return_value=session_context,
    ), patch(
        "app.workers.worker.JobProcessor",
    ) as processor_class:
        processor = processor_class.return_value
        processor.process = AsyncMock()

        before = metric_value(
            "asyncapi_worker_job_duration_seconds_count",
        )

        worker = Worker(queue)

        result = await worker.process_next()

        after = metric_value(
            "asyncapi_worker_job_duration_seconds_count",
        )

    assert result is True
    assert after == before + 1

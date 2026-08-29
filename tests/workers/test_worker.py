import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.worker import Worker


@pytest.mark.asyncio
async def test_process_next_returns_false_when_queue_is_empty():
    queue = MagicMock()
    queue.dequeue = AsyncMock(return_value=None)

    worker = Worker(queue)

    result = await worker.process_next()

    assert result is False
    queue.dequeue.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_next_processes_dequeued_job():
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

        worker = Worker(queue)

        result = await worker.process_next()

    assert result is True

    queue.dequeue.assert_awaited_once()
    processor.process.assert_awaited_once_with(123)
    processor_class.assert_called_once_with(session)


@pytest.mark.asyncio
async def test_process_next_requeues_job_when_processing_raises():
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

        worker = Worker(queue)

        with pytest.raises(
            RuntimeError,
            match="temporary processing failure",
        ):
            await worker.process_next()

    queue.dequeue.assert_awaited_once()
    queue.enqueue.assert_awaited_once_with(789)
    processor.process.assert_awaited_once_with(789)


@pytest.mark.asyncio
async def test_process_next_closes_session_after_processing():
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

        worker = Worker(queue)

        await worker.process_next()

    session_context.__aenter__.assert_awaited_once()
    session_context.__aexit__.assert_awaited_once()
    processor.process.assert_awaited_once_with(456)

@pytest.mark.asyncio
async def test_run_forever_survives_unexpected_processing_error():
    queue = MagicMock()
    worker = Worker(queue, poll_interval=0)

    stop_event = asyncio.Event()
    calls = 0

    async def process_next():
        nonlocal calls
        calls += 1

        if calls == 1:
            raise RuntimeError("temporary worker failure")

        stop_event.set()
        return False

    worker.process_next = process_next

    await worker.run_forever(stop_event)

    assert calls == 2
    assert stop_event.is_set()


@pytest.mark.asyncio
async def test_worker_logs_when_queue_is_empty(caplog):
    queue = MagicMock()
    queue.dequeue = AsyncMock(return_value=None)

    worker = Worker(queue)

    with caplog.at_level("INFO", logger="asyncapi.worker"):
        result = await worker.process_next()

    assert result is False
    assert "worker_queue_empty" in caplog.text


@pytest.mark.asyncio
async def test_worker_logs_successful_processing(caplog):
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

        worker = Worker(queue)

        with caplog.at_level("INFO", logger="asyncapi.worker"):
            result = await worker.process_next()

    assert result is True
    assert "worker_job_dequeued job_id=123" in caplog.text
    assert "worker_job_processed job_id=123" in caplog.text


@pytest.mark.asyncio
async def test_worker_logs_and_requeues_failed_processing(caplog):
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

        worker = Worker(queue)

        with caplog.at_level("INFO", logger="asyncapi.worker"):
            with pytest.raises(
                RuntimeError,
                match="temporary processing failure",
            ):
                await worker.process_next()

    assert "worker_job_dequeued job_id=789" in caplog.text
    assert (
        "worker_job_failed job_id=789 "
        "error=temporary processing failure"
    ) in caplog.text
    assert "worker_job_requeued job_id=789" in caplog.text

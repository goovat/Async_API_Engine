from unittest.mock import AsyncMock

import pytest

from app.workers.queue import JobQueue


@pytest.mark.asyncio
async def test_enqueue_pushes_job_id():
    queue = JobQueue("test:jobs")

    import app.workers.queue as queue_module

    queue_module.redis_client.rpush = AsyncMock()

    await queue.enqueue(123)

    queue_module.redis_client.rpush.assert_awaited_once_with(
        "test:jobs",
        "123",
    )


@pytest.mark.asyncio
async def test_dequeue_returns_job_id():
    queue = JobQueue("test:jobs")

    import app.workers.queue as queue_module

    queue_module.redis_client.lpop = AsyncMock(
        return_value="123",
    )

    result = await queue.dequeue()

    assert result == 123

    queue_module.redis_client.lpop.assert_awaited_once_with(
        "test:jobs",
    )


@pytest.mark.asyncio
async def test_dequeue_returns_none_when_queue_is_empty():
    queue = JobQueue("test:jobs")

    import app.workers.queue as queue_module

    queue_module.redis_client.lpop = AsyncMock(
        return_value=None,
    )

    result = await queue.dequeue()

    assert result is None


@pytest.mark.asyncio
async def test_size_returns_queue_length():
    queue = JobQueue("test:jobs")

    import app.workers.queue as queue_module

    queue_module.redis_client.llen = AsyncMock(
        return_value=4,
    )

    result = await queue.size()

    assert result == 4

from app.redis.client import redis_client


JOB_QUEUE_NAME = "asyncapi:jobs"


class JobQueue:
    def __init__(self, queue_name: str = JOB_QUEUE_NAME) -> None:
        self.queue_name = queue_name

    async def enqueue(self, job_id: int) -> None:
        await redis_client.rpush(
            self.queue_name,
            str(job_id),
        )

    async def dequeue(self) -> int | None:
        job_id = await redis_client.lpop(self.queue_name)

        if job_id is None:
            return None

        return int(job_id)

    async def size(self) -> int:
        return await redis_client.llen(self.queue_name)

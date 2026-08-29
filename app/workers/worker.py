import asyncio

from app.database.session import AsyncSessionLocal
from app.observability.logging import get_logger
from app.workers.job_processor import JobProcessor
from app.workers.queue import JobQueue


logger = get_logger("worker")


class Worker:
    def __init__(
        self,
        queue: JobQueue | None = None,
        poll_interval: float = 1.0,
    ) -> None:
        self.queue = queue or JobQueue()
        self.poll_interval = poll_interval

    async def process_next(self) -> bool:
        job_id = await self.queue.dequeue()

        if job_id is None:
            logger.info("worker_queue_empty")
            return False

        logger.info(
            "worker_job_dequeued job_id=%s",
            job_id,
        )

        try:
            async with AsyncSessionLocal() as session:
                processor = JobProcessor(session)
                await processor.process(job_id)
        except Exception as exc:
            logger.error(
                "worker_job_failed job_id=%s error=%s",
                job_id,
                str(exc),
                exc_info=True,
            )

            await self.queue.enqueue(job_id)

            logger.info(
                "worker_job_requeued job_id=%s",
                job_id,
            )

            raise

        logger.info(
            "worker_job_processed job_id=%s",
            job_id,
        )

        return True


    async def run_forever(
        self,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        stop_event = stop_event or asyncio.Event()

        while not stop_event.is_set():
            try:
                processed = await self.process_next()
            except Exception:
                try:
                    await asyncio.wait_for(
                        stop_event.wait(),
                        timeout=self.poll_interval,
                    )
                except asyncio.TimeoutError:
                    pass
                continue

            if not processed:
                try:
                    await asyncio.wait_for(
                        stop_event.wait(),
                        timeout=self.poll_interval,
                    )
                except asyncio.TimeoutError:
                    pass

import asyncio

from redis.asyncio import Redis

from app.config.settings import settings


class LoopSafeRedis:
    def __init__(self, url: str) -> None:
        self.url = url
        self._clients: dict[int, Redis] = {}

    def _get_client(self) -> Redis:
        loop = asyncio.get_running_loop()
        loop_id = id(loop)

        client = self._clients.get(loop_id)

        if client is None:
            client = Redis.from_url(
                self.url,
                decode_responses=True,
            )
            self._clients[loop_id] = client

        return client

    async def rpush(self, *args):
        return await self._get_client().rpush(*args)

    async def lpop(self, *args):
        return await self._get_client().lpop(*args)

    async def llen(self, *args):
        return await self._get_client().llen(*args)

    async def ping(self) -> bool:
        return await self._get_client().ping()

    async def close(self) -> None:
        clients = list(self._clients.values())
        self._clients.clear()

        for client in clients:
            await client.aclose()


redis_client = LoopSafeRedis(settings.redis_url)


async def close_redis() -> None:
    await redis_client.close()

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router
from app.config.settings import settings
from app.database.session import close_database
from app.redis.client import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    await close_redis()
    await close_database()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(router)

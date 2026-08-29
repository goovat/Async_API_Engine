from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router
from app.config.settings import settings
from app.database.session import close_database
from app.redis.client import close_redis
from app.middleware.request_id import RequestIDMiddleware
from app.observability.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    await close_redis()
    await close_database()


configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(RequestIDMiddleware)
app.include_router(router)

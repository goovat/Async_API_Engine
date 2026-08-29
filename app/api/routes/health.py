from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.database.session import AsyncSessionLocal
from app.redis.client import redis_client


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def readiness() -> dict[str, str]:
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        await redis_client.ping()

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Readiness check failed",
        ) from exc

    return {
        "status": "ready",
        "database": "ok",
        "redis": "ok",
    }

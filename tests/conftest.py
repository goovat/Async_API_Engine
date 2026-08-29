import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.models.user import User


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                TRUNCATE TABLE
                    job_attempts,
                    idempotency_keys,
                    jobs,
                    users
                RESTART IDENTITY CASCADE
                """
            )
        )
        await session.commit()

        user1 = User(
            id=1,
            email="test-user-1@example.com",
            password_hash="test-password-hash",
        )
        user2 = User(
            id=2,
            email="test-user-2@example.com",
            password_hash="test-password-hash",
        )

        session.add_all([user1, user2])
        await session.flush()

        yield session

        await session.rollback()

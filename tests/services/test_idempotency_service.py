import pytest

from app.models.idempotency_key import IdempotencyKey
from app.services.idempotency_service import IdempotencyService


@pytest.mark.asyncio
async def test_get_or_create_creates_new_key(db_session):
    service = IdempotencyService(db_session)

    record, created = await service.get_or_create(
        user_id=1,
        key="test-key",
    )

    assert created is True
    assert isinstance(record, IdempotencyKey)
    assert record.user_id == 1
    assert record.key == "test-key"


@pytest.mark.asyncio
async def test_get_or_create_returns_existing_key(
    db_session,
):
    service = IdempotencyService(db_session)

    first_record, first_created = await service.get_or_create(
        user_id=1,
        key="test-key",
    )

    second_record, second_created = await service.get_or_create(
        user_id=1,
        key="test-key",
    )

    assert first_created is True
    assert second_created is False

    assert second_record.id == first_record.id
    assert second_record.user_id == first_record.user_id
    assert second_record.key == first_record.key


@pytest.mark.asyncio
async def test_same_key_can_be_used_by_different_users(
    db_session,
):
    service = IdempotencyService(db_session)

    first_record, first_created = await service.get_or_create(
        user_id=1,
        key="same-key",
    )

    second_record, second_created = await service.get_or_create(
        user_id=2,
        key="same-key",
    )

    assert first_created is True
    assert second_created is True

    assert first_record.id != second_record.id
    assert first_record.user_id == 1
    assert second_record.user_id == 2
    assert first_record.key == second_record.key == "same-key"

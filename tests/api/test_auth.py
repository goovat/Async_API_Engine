import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.database import get_db
from app.database.session import AsyncSessionLocal
from app.main import app


async def override_get_db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def user_credentials():
    return {
        "email": f"test-{uuid.uuid4().hex}@example.com",
        "password": "test-password-123",
    }


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_user(client, user_credentials):
    response = client.post(
        "/auth/register",
        json=user_credentials,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["email"] == user_credentials["email"]


def test_duplicate_registration_returns_conflict(
    client,
    user_credentials,
):
    first_response = client.post(
        "/auth/register",
        json=user_credentials,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/auth/register",
        json=user_credentials,
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "User already exists"


def test_login_returns_access_token(
    client,
    user_credentials,
):
    register_response = client.post(
        "/auth/register",
        json=user_credentials,
    )

    assert register_response.status_code == 201

    response = client.post(
        "/auth/login",
        json=user_credentials,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["token_type"] == "bearer"


def test_authenticated_user_can_access_me(
    client,
    user_credentials,
):
    register_response = client.post(
        "/auth/register",
        json=user_credentials,
    )

    assert register_response.status_code == 201

    user_id = register_response.json()["id"]

    login_response = client.post(
        "/auth/login",
        json=user_credentials,
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == user_id
    assert data["email"] == user_credentials["email"]


def test_invalid_password_returns_unauthorized(
    client,
    user_credentials,
):
    register_response = client.post(
        "/auth/register",
        json=user_credentials,
    )

    assert register_response.status_code == 201

    response = client.post(
        "/auth/login",
        json={
            "email": user_credentials["email"],
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_missing_credentials_returns_unauthorized(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_invalid_token_returns_unauthorized(client):
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_readiness_endpoint_reports_healthy_dependencies(client):
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
        "redis": "ok",
    }


def test_readiness_endpoint_returns_server_error_when_database_fails(
    client,
):
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.api.routes.health.AsyncSessionLocal",
    ) as session_factory:
        session_context = session_factory.return_value
        session = session_context.__aenter__.return_value
        session.execute = AsyncMock(
            side_effect=RuntimeError("database unavailable"),
        )

        with patch(
            "app.api.routes.health.redis_client.ping",
            new=AsyncMock(),
        ):
            response = client.get("/ready")

    assert response.status_code == 500


def test_readiness_endpoint_returns_server_error_when_redis_fails(
    client,
):
    from unittest.mock import AsyncMock, patch

    with patch(
        "app.api.routes.health.AsyncSessionLocal",
    ) as session_factory:
        session_context = session_factory.return_value
        session = session_context.__aenter__.return_value
        session.execute = AsyncMock()

        with patch(
            "app.api.routes.health.redis_client.ping",
            new=AsyncMock(
                side_effect=RuntimeError("redis unavailable"),
            ),
        ):
            response = client.get("/ready")

    assert response.status_code == 500

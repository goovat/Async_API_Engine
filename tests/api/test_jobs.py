import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.database import get_db
from app.database.session import AsyncSessionLocal
from app.models.job import Job
from app.models.job_attempt import JobAttempt
from app.main import app


async def override_get_db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def client():
    import app.api.routes.jobs as jobs_module

    queue = MagicMock()
    queue.enqueue = AsyncMock()

    with patch.object(
        jobs_module,
        "JobQueue",
        return_value=queue,
    ):
        app.dependency_overrides[get_db] = override_get_db

        try:
            test_client = TestClient(app)
            test_client.queue = queue
            yield test_client
        finally:
            app.dependency_overrides.clear()


def unique_email() -> str:
    return f"job-test-{uuid.uuid4().hex}@example.com"


def register_and_login(client: TestClient) -> tuple[dict, str]:
    credentials = {
        "email": unique_email(),
        "password": "test-password-123",
    }

    register_response = client.post(
        "/auth/register",
        json=credentials,
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json=credentials,
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return credentials, token


def create_job(client: TestClient, token: str) -> dict:
    response = client.post(
        "/jobs",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "job_type": "example",
            "payload": '{"hello": "world"}',
        },
    )

    assert response.status_code == 201

    return response.json()


def test_created_job_is_enqueued(client):
    _, token = register_and_login(client)

    response = client.post(
        "/jobs",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "job_type": "example",
            "payload": '{"hello": "world"}',
        },
    )

    assert response.status_code == 201

    job_id = response.json()["id"]

    client.queue.enqueue.assert_awaited_once_with(job_id)

def test_authenticated_user_can_create_job(client):
    _, token = register_and_login(client)

    response = client.post(
        "/jobs",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "job_type": "example",
            "payload": '{"hello": "world"}',
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["job_type"] == "example"
    assert data["payload"] == '{"hello": "world"}'
    assert data["status"] == "pending"


def test_created_job_belongs_to_authenticated_user(client):
    _, token = register_and_login(client)

    response = client.post(
        "/jobs",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "job_type": "example",
            "payload": '{"value": 123}',
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] is not None


def test_authenticated_user_can_get_their_job(client):
    _, token = register_and_login(client)

    job = create_job(client, token)

    response = client.get(
        f"/jobs/{job['id']}",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == job["id"]
    assert data["user_id"] == job["user_id"]
    assert data["job_type"] == "example"
    assert data["payload"] == '{"hello": "world"}'
    assert data["status"] == "pending"


def test_user_cannot_get_another_users_job(client):
    _, first_token = register_and_login(client)

    job = create_job(client, first_token)

    _, second_token = register_and_login(client)

    response = client.get(
        f"/jobs/{job['id']}",
        headers={
            "Authorization": f"Bearer {second_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_authenticated_user_can_get_job_status(client):
    _, token = register_and_login(client)

    job = create_job(client, token)

    response = client.get(
        f"/jobs/{job['id']}/status",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "id": job["id"],
        "status": "pending",
    }


def test_missing_job_returns_not_found(client):
    _, token = register_and_login(client)

    response = client.get(
        "/jobs/999999999",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_missing_job_status_returns_not_found(client):
    _, token = register_and_login(client)

    response = client.get(
        "/jobs/999999999/status",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_unauthenticated_user_cannot_create_job(client):
    response = client.post(
        "/jobs",
        json={
            "job_type": "example",
            "payload": '{"hello": "world"}',
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_unauthenticated_user_cannot_get_job(client):
    response = client.get("/jobs/1")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_unauthenticated_user_cannot_get_job_status(client):
    response = client.get("/jobs/1/status")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_invalid_job_payload_is_rejected(client):
    _, token = register_and_login(client)

    response = client.post(
        "/jobs",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "job_type": "",
            "payload": "",
        },
    )

    assert response.status_code == 422

def test_authenticated_user_can_retry_their_job(client):
    _, token = register_and_login(client)

    job = create_job(client, token)

    async def mark_job_failed():
        async with AsyncSessionLocal() as session:
            db_job = await session.get(Job, job["id"])

            if db_job is None:
                raise RuntimeError("Test job was not created.")

            db_job.status = "failed"
            await session.commit()

    import asyncio
    asyncio.run(mark_job_failed())

    response = client.post(
        f"/jobs/{job['id']}/retry",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == job["id"]
    assert data["user_id"] == job["user_id"]
    assert data["status"] == "pending"

    client.queue.enqueue.assert_awaited_once_with(job["id"])


def test_processing_job_retry_returns_conflict(client):
    _, token = register_and_login(client)

    job = create_job(client, token)
    client.queue.enqueue.reset_mock()

    async def mark_job_processing():
        async with AsyncSessionLocal() as session:
            db_job = await session.get(Job, job["id"])

            if db_job is None:
                raise RuntimeError("Test job was not created.")

            db_job.status = "processing"
            await session.commit()

    import asyncio
    asyncio.run(mark_job_processing())

    response = client.post(
        f"/jobs/{job['id']}/retry",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Only failed jobs can be retried"
    )

    client.queue.enqueue.assert_not_awaited()


def test_completed_job_retry_returns_conflict(client):
    _, token = register_and_login(client)

    job = create_job(client, token)
    client.queue.enqueue.reset_mock()

    async def mark_job_completed():
        async with AsyncSessionLocal() as session:
            db_job = await session.get(Job, job["id"])

            if db_job is None:
                raise RuntimeError("Test job was not created.")

            db_job.status = "completed"
            await session.commit()

    import asyncio
    asyncio.run(mark_job_completed())

    response = client.post(
        f"/jobs/{job['id']}/retry",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Only failed jobs can be retried"
    )

    client.queue.enqueue.assert_not_awaited()


def test_max_retry_attempts_returns_conflict(client):
    _, token = register_and_login(client)

    job = create_job(client, token)
    client.queue.enqueue.reset_mock()

    async def prepare_failed_job_with_max_attempts():
        async with AsyncSessionLocal() as session:
            db_job = await session.get(Job, job["id"])

            if db_job is None:
                raise RuntimeError("Test job was not created.")

            db_job.status = "failed"

            for attempt_number in range(1, 4):
                session.add(
                    JobAttempt(
                        job_id=job["id"],
                        attempt_number=attempt_number,
                        status="failed",
                        error_message="temporary failure",
                    )
                )

            await session.commit()

    import asyncio
    asyncio.run(prepare_failed_job_with_max_attempts())

    response = client.post(
        f"/jobs/{job['id']}/retry",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Maximum retry attempts reached"
    )

    client.queue.enqueue.assert_not_awaited()

def test_user_cannot_retry_another_users_job(client):
    _, first_token = register_and_login(client)

    job = create_job(client, first_token)

    _, second_token = register_and_login(client)

    response = client.post(
        f"/jobs/{job['id']}/retry",
        headers={
            "Authorization": f"Bearer {second_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_missing_job_retry_returns_not_found(client):
    _, token = register_and_login(client)

    response = client.post(
        "/jobs/999999999/retry",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_unauthenticated_user_cannot_retry_job(client):
    response = client.post("/jobs/1/retry")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"

def test_same_idempotency_key_returns_same_job(client):
    _, token = register_and_login(client)

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Idempotency-Key": "create-job-123",
    }

    payload = {
        "job_type": "example",
        "payload": '{"hello": "world"}',
    }

    first_response = client.post(
        "/jobs",
        headers=headers,
        json=payload,
    )

    assert first_response.status_code == 201

    first_data = first_response.json()
    first_job_id = first_data["id"]

    client.queue.enqueue.reset_mock()

    second_response = client.post(
        "/jobs",
        headers=headers,
        json=payload,
    )

    assert second_response.status_code == 201

    second_data = second_response.json()

    assert second_data == first_data

    client.queue.enqueue.assert_not_awaited()


def test_same_idempotency_key_is_scoped_to_user(client):
    _, first_token = register_and_login(client)
    _, second_token = register_and_login(client)

    first_response = client.post(
        "/jobs",
        headers={
            "Authorization": f"Bearer {first_token}",
            "X-Idempotency-Key": "shared-key",
        },
        json={
            "job_type": "example",
            "payload": '{"owner": "first"}',
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/jobs",
        headers={
            "Authorization": f"Bearer {second_token}",
            "X-Idempotency-Key": "shared-key",
        },
        json={
            "job_type": "example",
            "payload": '{"owner": "second"}',
        },
    )

    assert second_response.status_code == 201

    assert (
        second_response.json()["id"]
        != first_response.json()["id"]
    )


def test_different_idempotency_keys_create_different_jobs(client):
    _, token = register_and_login(client)

    payload = {
        "job_type": "example",
        "payload": '{"hello": "world"}',
    }

    first_response = client.post(
        "/jobs",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Idempotency-Key": "key-one",
        },
        json=payload,
    )

    assert first_response.status_code == 201

    client.queue.enqueue.reset_mock()

    second_response = client.post(
        "/jobs",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Idempotency-Key": "key-two",
        },
        json=payload,
    )

    assert second_response.status_code == 201

    assert (
        second_response.json()["id"]
        != first_response.json()["id"]
    )

    client.queue.enqueue.assert_awaited_once_with(
        second_response.json()["id"]
    )


def test_authenticated_user_can_get_job_attempts(client):
    _, token = register_and_login(client)

    job = create_job(client, token)

    response = client.get(
        f"/jobs/{job['id']}/attempts",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_user_cannot_get_another_users_job_attempts(client):
    _, first_token = register_and_login(client)

    job = create_job(client, first_token)

    _, second_token = register_and_login(client)

    response = client.get(
        f"/jobs/{job['id']}/attempts",
        headers={
            "Authorization": f"Bearer {second_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_missing_job_attempts_returns_not_found(client):
    _, token = register_and_login(client)

    response = client.get(
        "/jobs/999999999/attempts",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_unauthenticated_user_cannot_get_job_attempts(client):
    response = client.get("/jobs/1/attempts")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"


def test_authenticated_user_can_get_job_attempts(client):
    _, token = register_and_login(client)

    job = create_job(client, token)

    response = client.get(
        f"/jobs/{job['id']}/attempts",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_user_cannot_get_another_users_job_attempts(client):
    _, first_token = register_and_login(client)

    job = create_job(client, first_token)

    _, second_token = register_and_login(client)

    response = client.get(
        f"/jobs/{job['id']}/attempts",
        headers={
            "Authorization": f"Bearer {second_token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_missing_job_attempts_returns_not_found(client):
    _, token = register_and_login(client)

    response = client.get(
        "/jobs/999999999/attempts",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"


def test_unauthenticated_user_cannot_get_job_attempts(client):
    response = client.get("/jobs/1/attempts")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authentication credentials"

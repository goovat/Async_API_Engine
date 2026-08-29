from fastapi.testclient import TestClient

from app.main import app


def test_request_id_is_generated_when_missing():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200

    request_id = response.headers.get("X-Request-ID")

    assert request_id is not None
    assert request_id != ""


def test_existing_request_id_is_preserved():
    client = TestClient(app)

    request_id = "test-request-123"

    response = client.get(
        "/health",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_request_id_is_unique_between_requests():
    client = TestClient(app)

    first_response = client.get("/health")
    second_response = client.get("/health")

    first_request_id = first_response.headers["X-Request-ID"]
    second_request_id = second_response.headers["X-Request-ID"]

    assert first_request_id != second_request_id

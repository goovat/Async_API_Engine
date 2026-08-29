from fastapi.testclient import TestClient

from app.main import app


def test_metrics_endpoint_returns_prometheus_metrics():
    client = TestClient(app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "asyncapi_http_requests_total" in response.text
    assert "asyncapi_http_request_duration_seconds" in response.text


def test_metrics_endpoint_records_http_request():
    client = TestClient(app)

    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert 'asyncapi_http_requests_total{method="GET",path="/health",status="200"}' in response.text


def test_metrics_endpoint_records_request_duration():
    client = TestClient(app)

    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert 'asyncapi_http_request_duration_seconds_count{method="GET",path="/health"}' in response.text

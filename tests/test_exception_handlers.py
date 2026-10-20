
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app
from app.utils.exception_handlers import app_exception_handler
from app.utils.exceptions import AppException


def test_app_exception_returns_standard_response():
    test_app = FastAPI()
    test_app.add_exception_handler(
    AppException,
    app_exception_handler,
)

    @test_app.get("/test-error")
    def trigger_error():
        raise AppException(
            detail="Test error.",
            status_code=418,
            code="TEST_ERROR",
        )

    with TestClient(test_app) as client:
        response = client.get("/test-error")

    assert response.status_code == 418
    assert response.json() == {
        "error": {
            "code": "TEST_ERROR",
            "message": "Test error.",
        }
    }


def test_validation_error_returns_standard_response():
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "username": "analyst",
                "password": "short",
            },
        )

    assert response.status_code == 422

    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Request validation failed."
    assert body["error"]["details"]
    assert all("input" not in item for item in body["error"]["details"])

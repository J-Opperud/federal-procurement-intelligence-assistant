
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ResearchQuery, User


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Provide an API client backed by an isolated test database."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db() -> Generator[Session, None, None]:
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_register_creates_user_without_exposing_password_hash(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "analyst",
            "password": "Scout-Test-Password-123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["username"] == "analyst"
    assert "hashed_password" not in response.json()
    assert "password" not in response.json()


def test_register_rejects_duplicate_username(client):
    payload = {
        "username": "analyst",
        "password": "Scout-Test-Password-123!",
    }

    first_response = client.post("/auth/register", json=payload)
    second_response = client.post("/auth/register", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_login_returns_access_token(client):
    client.post(
        "/auth/register",
        json={
            "username": "analyst",
            "password": "Scout-Test-Password-123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "username": "analyst",
            "password": "Scout-Test-Password-123!",
        },
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_rejects_incorrect_password(client):
    client.post(
        "/auth/register",
        json={
            "username": "analyst",
            "password": "Scout-Test-Password-123!",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "username": "analyst",
            "password": "Wrong-Password-456!",
        },
    )

    assert response.status_code == 401


def test_current_user_requires_authentication(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_current_user_returns_authenticated_profile(client):
    client.post(
        "/auth/register",
        json={
            "username": "analyst",
            "password": "Scout-Test-Password-123!",
        },
    )

    login_response = client.post(
        "/auth/login",
        json={
            "username": "analyst",
            "password": "Scout-Test-Password-123!",
        },
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "analyst"
    assert "hashed_password" not in response.json()

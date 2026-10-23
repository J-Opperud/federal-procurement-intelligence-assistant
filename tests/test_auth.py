
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
        "/auth/token",
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
        "/auth/token",
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
        "/auth/token",
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
import pytest


@pytest.mark.parametrize(
    "username,password",
    [
        ("ab", "Scout-Test-Password-123!"),
        ("analyst", "short"),
        ("analyst", "x" * 129),
        ("invalid username", "Scout-Test-Password-123!"),
        ("analyst!", "Scout-Test-Password-123!"),
    ],
)
def test_registration_rejects_invalid_account_data(
    client,
    username,
    password,
):
    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 422


def test_registration_accepts_minimum_password_length(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "valid_analyst",
            "password": "A" * 15,
        },
    )

    assert response.status_code == 201


def test_registration_accepts_maximum_password_length(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "valid_analyst",
            "password": "A" * 128,
        },
    )

    assert response.status_code == 201


def test_registration_trims_and_normalizes_username(client):
    response = client.post(
        "/auth/register",
        json={
            "username": "  Analyst_01  ",
            "password": "Scout-Test-Password-123!",
        },
    )

    assert response.status_code == 201
    assert response.json()["username"] == "analyst_01"

def test_login_trims_and_normalizes_username(client):
    password = "Scout-Test-Password-123!"

    registration = client.post(
        "/auth/register",
        json={
            "username": "Analyst_01",
            "password": password,
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/auth/token",
        json={
            "username": "  ANALYST_01  ",
            "password": password,
        },
    )

    assert login.status_code == 200
    assert login.json()["access_token"]


def test_registration_does_not_store_plaintext_password(client):
    from sqlalchemy import select

    from app.models import User

    password = "Scout-Test-Password-123!"

    response = client.post(
        "/auth/register",
        json={
            "username": "secure_analyst",
            "password": password,
        },
    )

    assert response.status_code == 201

    db_override = app.dependency_overrides[get_db]
    generator = db_override()
    db = next(generator)

    try:
        user = db.scalar(
            select(User).where(
                User.username == "secure_analyst"
            )
        )

        assert user is not None
        assert user.hashed_password != password
        assert user.hashed_password
        assert password not in user.hashed_password
    finally:
        generator.close()

def test_registration_stores_only_password_hash(client):
    from sqlalchemy import select

    from app.database import get_db
    from app.models import User

    password = "Scout-Test-Password-123!"

    response = client.post(
        "/auth/register",
        json={
            "username": "hash_check_user",
            "password": password,
        },
    )

    assert response.status_code == 201

    db_override = app.dependency_overrides[get_db]
    generator = db_override()
    db = next(generator)

    try:
        user = db.scalar(
            select(User).where(
                User.username == "hash_check_user"
            )
        )

        assert user is not None
        assert user.hashed_password != password
        assert password not in user.hashed_password
    finally:
        generator.close()


def test_registration_response_never_exposes_password_or_hash(client):
    password = "Scout-Test-Password-123!"

    response = client.post(
        "/auth/register",
        json={
            "username": "response_check_user",
            "password": password,
        },
    )

    assert response.status_code == 201

    response_text = response.text.lower()

    assert password not in response.text
    assert "hashed_password" not in response_text
    assert "secret_key" not in response_text
    assert "signing_secret" not in response_text

def _register_and_login(client, username):
    client.post(
        "/auth/register",
        json={
            "username": username,
            "password": "Scout-Test-Password-123!",
        },
    )
    response = client.post(
        "/auth/token",
        json={
            "username": username,
            "password": "Scout-Test-Password-123!",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_create_research_query_uses_authenticated_owner(client):
    from sqlalchemy import select

    token = _register_and_login(client, "research_owner")
    profile_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code == 200
    expected_user_id = profile_response.json()["id"]

    response = client.post(
        "/research/queries",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "question": "Find open cybersecurity contracts",
            "answer": "Two matching opportunities found.",
            "sources": [{"sam_notice_id": "SAM-123"}],
            "sufficient_evidence": True,
        },
    )

    assert response.status_code == 201
    result = response.json()
    assert result["user_id"] == expected_user_id
    assert result["question"] == "Find open cybersecurity contracts"
    assert result["answer"] == "Two matching opportunities found."
    assert result["sources"] == [{"sam_notice_id": "SAM-123"}]
    assert result["sufficient_evidence"] is True
    assert result["created_at"]

    db_override = app.dependency_overrides[get_db]
    generator = db_override()
    db = next(generator)
    try:
        saved_query = db.scalar(
            select(ResearchQuery).where(
                ResearchQuery.id == result["id"]
            )
        )
        assert saved_query is not None
        assert saved_query.user_id == expected_user_id
        assert saved_query.sources_json
        assert saved_query.sources_json == (
            '[{"sam_notice_id": "SAM-123"}]'
        )
    finally:
        generator.close()


def test_create_research_query_rejects_client_supplied_user_id(client):
    token = _register_and_login(client, "research_no_impersonation")

    response = client.post(
        "/research/queries",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_id": 999999,
            "question": "Find open cybersecurity contracts",
            "answer": "Two matching opportunities found.",
            "sources": [],
            "sufficient_evidence": True,
        },
    )

    assert response.status_code == 422


def test_create_research_query_requires_authentication(client):
    response = client.post(
        "/research/queries",
        json={
            "question": "Find open cybersecurity contracts",
            "answer": "Two matching opportunities found.",
            "sources": [],
            "sufficient_evidence": True,
        },
    )

    assert response.status_code == 401


def test_research_history_is_private_to_authenticated_user(client):
    token_one = _register_and_login(client, "history_owner_one")
    token_two = _register_and_login(client, "history_owner_two")

    headers_one = {"Authorization": f"Bearer {token_one}"}
    headers_two = {"Authorization": f"Bearer {token_two}"}

    response_one = client.post(
        "/research/queries",
        headers=headers_one,
        json={
            "question": "Question belonging to user one",
            "answer": "Answer for user one",
            "sources": [{"source": "one"}],
            "sufficient_evidence": True,
        },
    )
    response_two = client.post(
        "/research/queries",
        headers=headers_two,
        json={
            "question": "Question belonging to user two",
            "answer": "Answer for user two",
            "sources": [{"source": "two"}],
            "sufficient_evidence": False,
        },
    )

    assert response_one.status_code == 201
    assert response_two.status_code == 201

    history_one = client.get(
        "/research/queries",
        headers=headers_one,
    )
    history_two = client.get(
        "/research/queries",
        headers=headers_two,
    )

    assert history_one.status_code == 200
    assert history_two.status_code == 200

    results_one = history_one.json()
    results_two = history_two.json()

    assert [item["question"] for item in results_one] == [
        "Question belonging to user one"
    ]
    assert [item["question"] for item in results_two] == [
        "Question belonging to user two"
    ]

    assert all(
        item["user_id"] == response_one.json()["user_id"]
        for item in results_one
    )
    assert all(
        item["user_id"] == response_two.json()["user_id"]
        for item in results_two
    )


def test_research_history_requires_authentication(client):
    response = client.get("/research/queries")

    assert response.status_code == 401

def test_login_allows_password_shorter_than_registration_minimum(client):
    response = client.post(
        "/auth/token",
        json={
            "username": "analyst",
            "password": "short",
        },
    )

    # The input passes validation; invalid credentials return 401.
    assert response.status_code == 401

def test_login_response_never_exposes_password_or_hash(client):
    password = "Scout-Test-Password-123!"

    client.post(
        "/auth/register",
        json={"username": "login_security_user", "password": password},
    )

    response = client.post(
        "/auth/token",
        json={"username": "login_security_user", "password": password},
    )

    assert response.status_code == 200

    response_text = response.text.lower()
    assert password not in response.text
    assert "hashed_password" not in response_text
    assert "password" not in response.json()
    assert "hashed_password" not in response.json()

def test_current_user_rejects_invalid_bearer_token(client):
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
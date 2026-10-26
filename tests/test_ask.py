"""Tests for authenticated, evidence-grounded RAG question answering."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ResearchQuery


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, session_factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def authenticated_client(client):
    test_client, session_factory = client
    test_client.post(
        "/auth/register",
        json={
            "username": "ask-analyst",
            "password": "Scout-Test-Password-123!",
        },
    )
    token_response = test_client.post(
        "/auth/token",
        json={
            "username": "ask-analyst",
            "password": "Scout-Test-Password-123!",
        },
    )
    test_client.headers.update(
        {"Authorization": f"Bearer {token_response.json()['access_token']}"}
    )
    return test_client, session_factory


def test_ask_requires_authentication(client):
    response = client[0].post(
        "/ask",
        json={"question": "What is the deadline?"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize("question", ["", "    ", "tiny", "x" * 2001])
def test_ask_rejects_invalid_questions(client, question):
    test_client, _ = authenticated_client(client)

    response = test_client.post("/ask", json={"question": question})

    assert response.status_code == 422


def test_ask_generates_and_persists_answer_with_provenance(
    client,
    monkeypatch,
):
    from app.routers import ask

    test_client, session_factory = authenticated_client(client)
    evidence = [
        {
            "text": "The RFI requests secure cloud hosting.",
            "source_document_id": 17,
            "procurement_notice_id": 4,
            "title": "Cloud RFI",
            "source_type": "RFI",
            "source_url": "https://sam.gov/notice/123",
            "content_hash": "a" * 64,
            "chunk_index": 2,
            "distance": 0.12,
        }
    ]

    monkeypatch.setattr(
        ask,
        "retrieve_evidence",
        lambda *args, **kwargs: evidence,
    )
    monkeypatch.setattr(
        ask,
        "generate_answer",
        lambda question, passages: (
            "The RFI requests secure cloud hosting [S1]."
        ),
    )

    response = test_client.post(
        "/ask",
        json={"question": "What does the RFI request?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sufficient_evidence"] is True
    assert body["sources"][0]["source_document_id"] == 17
    assert body["sources"][0]["content_hash"] == "a" * 64
    assert body["sources"][0]["chunk_index"] == 2

    with session_factory() as db:
        saved = db.scalar(
            select(ResearchQuery).where(
                ResearchQuery.id == body["research_query_id"]
            )
        )
        assert saved.user_id > 0
        assert saved.sufficient_evidence is True
        assert (
            json.loads(saved.sources_json)[0]["source_document_id"]
            == 17
        )


def test_ask_reports_insufficient_evidence_without_calling_ollama(
    client,
    monkeypatch,
):
    from app.routers import ask

    test_client, session_factory = authenticated_client(client)

    monkeypatch.setattr(
        ask,
        "retrieve_evidence",
        lambda *args, **kwargs: [],
    )

    def unexpected_generation(*args, **kwargs):
        pytest.fail(
            "Ollama must not be called when evidence is insufficient"
        )

    monkeypatch.setattr(ask, "generate_answer", unexpected_generation)

    response = test_client.post(
        "/ask",
        json={"question": "Which agency issued this RFI?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sufficient_evidence"] is False
    assert body["sources"] == []
    assert "do not establish" in body["answer"]

    with session_factory() as db:
        saved = db.get(ResearchQuery, body["research_query_id"])
        assert saved.sufficient_evidence is False
        assert saved.sources_json == "[]"
"""Endpoint tests for local procurement search and SAM.gov synchronization."""

from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ProcurementNotice


@pytest.fixture
def document_api() -> Generator[tuple[TestClient, dict[str, str], sessionmaker], None, None]:
    """Provide an authenticated client and isolated in-memory database."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db() -> Generator[Session, None, None]:
        with testing_session_local() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            registration = client.post(
                "/auth/register",
                json={
                    "username": "document-tester",
                    "password": "Scout-Test-Password-123!",
                },
            )
            assert registration.status_code == 201
            login = client.post(
                "/auth/token",
                json={
                    "username": "document-tester",
                    "password": "Scout-Test-Password-123!",
                },
            )
            assert login.status_code == 200
            headers = {
                "Authorization": f"Bearer {login.json()['access_token']}"
            }
            yield client, headers, testing_session_local
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def seed_notice(
    session_factory: sessionmaker,
    *,
    sam_notice_id: str,
    title: str,
    notice_type: str,
    posted_date: datetime | None,
    description: str = "",
    department: str = "Department of Defense",
) -> None:
    """Insert one notice into the test database."""
    with session_factory() as session:
        session.add(
            ProcurementNotice(
                sam_notice_id=sam_notice_id,
                title=title,
                notice_type=notice_type,
                posted_date=posted_date,
                description=description,
                department=department,
                source_url=f"https://sam.gov/notice/{sam_notice_id}",
            )
        )
        session.commit()


@pytest.fixture
def seeded_document_api(document_api):
    """Provide a client with notices suitable for filter and pagination tests."""
    client, headers, session_factory = document_api
    seed_notice(
        session_factory,
        sam_notice_id="SAM-FILTER-001",
        title="Secure communications equipment",
        notice_type="Solicitation",
        posted_date=datetime(2026, 10, 1, 9, 30, tzinfo=timezone.utc),
        description="Radio equipment procurement",
    )
    seed_notice(
        session_factory,
        sam_notice_id="SAM-FILTER-002",
        title="Aircraft maintenance support",
        notice_type="Sources Sought",
        posted_date=datetime(2026, 10, 15, 16, 45, tzinfo=timezone.utc),
        description="Maintenance services",
        department="Department of the Air Force",
    )
    seed_notice(
        session_factory,
        sam_notice_id="SAM-FILTER-003",
        title="Secure network upgrade",
        notice_type="Solicitation",
        posted_date=datetime(2026, 10, 31, 23, 59, tzinfo=timezone.utc),
        description="Network infrastructure",
    )
    return client, headers, session_factory


def test_keyword_filter_matches_notice_content(seeded_document_api):
    client, headers, _ = seeded_document_api
    response = client.get("/documents", params={"keyword": "secure"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["sam_notice_id"] for item in body["items"]} == {
        "SAM-FILTER-001", "SAM-FILTER-003"
    }


def test_notice_type_filter_matches_case_insensitively(seeded_document_api):
    client, headers, _ = seeded_document_api
    response = client.get(
        "/documents", params={"notice_type": "solicitation"}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert all(item["notice_type"] == "Solicitation" for item in body["items"])


def test_posted_date_filters_include_both_calendar_boundaries(seeded_document_api):
    client, headers, _ = seeded_document_api
    response = client.get(
        "/documents",
        params={"posted_from": "2026-10-15", "posted_to": "2026-10-31"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["sam_notice_id"] for item in body["items"]} == {
        "SAM-FILTER-002", "SAM-FILTER-003"
    }


def test_search_returns_typed_pagination_metadata(seeded_document_api):
    client, headers, _ = seeded_document_api
    response = client.get("/documents", params={"page": 2, "page_size": 1}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 2
    assert body["page_size"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["sam_notice_id"] == "SAM-FILTER-002"


def test_search_returns_empty_items_when_no_results(document_api):
    client, headers, _ = document_api
    response = client.get("/documents", params={"keyword": "not-found"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}


@pytest.mark.parametrize("page_size", [0, 101, -1])
def test_search_rejects_invalid_page_size(document_api, page_size):
    client, headers, _ = document_api
    response = client.get("/documents", params={"page_size": page_size}, headers=headers)
    assert response.status_code == 422


def test_search_accepts_maximum_page_size(seeded_document_api):
    client, headers, _ = seeded_document_api
    response = client.get("/documents", params={"page_size": 100}, headers=headers)
    assert response.status_code == 200
    assert response.json()["page_size"] == 100


def test_search_rejects_reversed_date_range(document_api):
    client, headers, _ = document_api
    response = client.get(
        "/documents",
        params={"posted_from": "2026-10-20", "posted_to": "2026-10-01"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["keyword", "notice_type"])
def test_search_rejects_blank_filter(document_api, field):
    client, headers, _ = document_api
    response = client.get("/documents", params={field: "   "}, headers=headers)
    assert response.status_code == 422


def test_get_document_returns_matching_notice(seeded_document_api):
    client, headers, _ = seeded_document_api
    response = client.get("/documents/SAM-FILTER-002", headers=headers)
    assert response.status_code == 200
    assert response.json()["sam_notice_id"] == "SAM-FILTER-002"
    assert response.json()["title"] == "Aircraft maintenance support"


def test_get_document_returns_404_for_missing_notice(document_api):
    client, headers, _ = document_api
    response = client.get("/documents/DOES-NOT-EXIST", headers=headers)
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/documents", {}),
        ("get", "/documents/SAM-MISSING", {}),
        (
            "post",
            "/documents/sync",
            {"json": {"posted_from": "2026-10-01", "posted_to": "2026-10-02"}},
        ),
    ],
)
def test_all_document_endpoints_require_authentication(document_api, method, path, kwargs):
    client, _, _ = document_api
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"posted_from": "2026-10-03", "posted_to": "2026-10-02"},
        {"posted_from": "2025-01-01", "posted_to": "2026-01-02"},
        {"posted_from": "2026-10-01", "posted_to": "2026-10-02", "limit": 0},
        {"posted_from": "2026-10-01", "posted_to": "2026-10-02", "limit": 1001},
        {"posted_from": "2026-10-01", "posted_to": "2026-10-02", "notice_type": " "},
    ],
)
def test_sync_rejects_invalid_parameters(document_api, payload):
    client, headers, _ = document_api
    response = client.post("/documents/sync", json=payload, headers=headers)
    assert response.status_code == 422


def test_sync_inserts_updates_and_reports_counts(document_api, monkeypatch):
    client, headers, session_factory = document_api
    from app.services.chroma_evidence_service import IndexingResult
    monkeypatch.setattr(
        "app.routers.documents.index_procurement_notice",
        lambda db, notice: IndexingResult(1, False, "test-hash"),
    )
    seed_notice(
        session_factory,
        sam_notice_id="SAM-UPDATE-001",
        title="Old title",
        notice_type="Solicitation",
        posted_date=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    opportunities: list[dict[str, Any]] = [
        {
            "noticeId": "SAM-UPDATE-001",
            "title": "Updated title",
            "type": "Solicitation",
            "postedDate": "10/01/2026",
        },
        {
            "noticeId": "SAM-INSERT-001",
            "title": "New notice",
            "type": "Solicitation",
            "postedDate": "10/02/2026",
        },
        {
            "noticeId": "SAM-OTHER-001",
            "title": "Other type",
            "type": "Sources Sought",
            "postedDate": "10/02/2026",
        },
    ]
    mock_client = Mock()
    mock_client.search_opportunities.return_value = {"opportunities": opportunities}
    monkeypatch.setattr("app.routers.documents.SamGovClient", lambda: mock_client)

    response = client.post(
        "/documents/sync",
        json={
            "posted_from": "2026-10-01",
            "posted_to": "2026-10-31",
            "notice_type": "Solicitation",
            "limit": 50,
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "fetched_count": 3,
        "inserted_count": 1,
        "updated_count": 1,
        "indexed_count": 2,
        "failed_count": 0,
    }
    mock_client.search_opportunities.assert_called_once_with(
        posted_from="10/01/2026", posted_to="10/31/2026", limit=50
    )
    with session_factory() as session:
        updated = session.scalar(
            select(ProcurementNotice).where(
                ProcurementNotice.sam_notice_id == "SAM-UPDATE-001"
            )
        )
        assert updated.title == "Updated title"
        assert session.scalar(
            select(ProcurementNotice).where(
                ProcurementNotice.sam_notice_id == "SAM-OTHER-001"
            )
        ) is None


def test_sync_counts_invalid_notice_as_failed(document_api, monkeypatch):
    client, headers, _ = document_api
    from app.services.chroma_evidence_service import IndexingResult
    monkeypatch.setattr(
        "app.routers.documents.index_procurement_notice",
        lambda db, notice: IndexingResult(1, False, "test-hash"),
    )
    mock_client = Mock()
    mock_client.search_opportunities.return_value = {
        "opportunities": [
            {"noticeId": "", "title": "Invalid", "type": "Solicitation"},
            {
                "noticeId": "SAM-VALID-001",
                "title": "Valid notice",
                "type": "Solicitation",
                "postedDate": "10/02/2026",
            },
        ]
    }
    monkeypatch.setattr("app.routers.documents.SamGovClient", lambda: mock_client)
    response = client.post(
        "/documents/sync",
        json={"posted_from": "2026-10-01", "posted_to": "2026-10-31"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["fetched_count"] == 2
    assert response.json()["inserted_count"] == 1
    assert response.json()["failed_count"] == 1


def test_search_does_not_call_sam_gov(seeded_document_api, monkeypatch):
    client, headers, _ = seeded_document_api
    sam_client = Mock(side_effect=AssertionError("search must remain local"))
    monkeypatch.setattr("app.routers.documents.SamGovClient", sam_client)
    response = client.get("/documents", headers=headers)
    assert response.status_code == 200
    sam_client.assert_not_called()

"""Tests for Sentinel's adapted semantic-search ingestion pipeline."""
from datetime import timezone

import pytest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ProcurementNotice, SourceDocument
from app.services.document_chunking import chunk_text
from app.services.source_ingestion import (
    content_sha256,
    extract_document_text,
    index_source_document,
    retrieve_evidence,
)


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'source-ingestion.db').as_posix()}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with session_factory() as session:
        yield session
    engine.dispose()


class FakeEmbeddingModel:
    def encode(self, texts, show_progress_bar=False):
        if isinstance(texts, str):
            return [float(len(texts)), 1.0]
        return [[float(len(text)), float(index + 1)] for index, text in enumerate(texts)]


class FakeCollection:
    def __init__(self):
        self.records = {}
        self.last_query = None

    def get(self, where=None, include=None):
        source_id = where["source_document_id"]
        ids = [
            record_id for record_id, record in self.records.items()
            if record["metadata"]["source_document_id"] == source_id
        ]
        return {"ids": ids, "metadatas": [self.records[item]["metadata"] for item in ids]}

    def upsert(self, ids, documents, embeddings, metadatas):
        for record_id, document, embedding, metadata in zip(
            ids, documents, embeddings, metadatas, strict=True
        ):
            self.records[record_id] = {
                "document": document,
                "embedding": embedding,
                "metadata": metadata,
            }

    def delete(self, ids):
        for record_id in ids:
            self.records.pop(record_id, None)

    def count(self):
        return len(self.records)

    def query(self, **kwargs):
        self.last_query = kwargs
        records = list(self.records.values())[: kwargs["n_results"]]
        return {
            "documents": [[item["document"] for item in records]],
            "metadatas": [[item["metadata"] for item in records]],
            "distances": [[0.12 for _ in records]],
        }


def make_source(db_session, text=None):
    notice = ProcurementNotice(
        sam_notice_id="SAM-INGEST-001",
        title="Research computing equipment",
        notice_type="Solicitation",
    )
    db_session.add(notice)
    db_session.flush()
    source = SourceDocument(
        procurement_notice_id=notice.id,
        title="Technical requirements",
        source_type="attachment",
        source_url="https://example.gov/attachment.pdf",
        extracted_text=text,
    )
    db_session.add(source)
    db_session.flush()
    return source


def test_chunk_text_matches_expected_overlap_behavior():
    assert chunk_text("abcdefgh", chunk_size=5, overlap=2) == ["abcde", "defgh"]


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (5, -1), (5, 5)],
)
def test_chunk_text_rejects_invalid_parameters(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_text("content", chunk_size=chunk_size, overlap=overlap)


def test_chunk_text_returns_empty_for_whitespace():
    assert chunk_text(" \n ") == []


def test_content_hash_normalizes_newlines():
    assert content_sha256("a\r\nb") == content_sha256("a\nb")


def test_extract_document_text_supports_markdown(tmp_path):
    path = tmp_path / "requirements.md"
    path.write_text("  Required capability  ", encoding="utf-8")
    assert extract_document_text(path) == "Required capability"


def test_extract_document_text_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "requirements.docx"
    path.write_bytes(b"not supported")
    with pytest.raises(ValueError, match="Unsupported"):
        extract_document_text(path)


def test_extract_document_text_rejects_empty_content(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text(" \n ", encoding="utf-8")
    with pytest.raises(ValueError, match="No extractable text"):
        extract_document_text(path)


def test_index_source_document_persists_hash_and_provenance(db_session):
    source = make_source(db_session)
    collection = FakeCollection()
    result = index_source_document(
        db_session,
        source,
        "A procurement requires secure cloud hosting and technical support.",
        collection=collection,
        embedding_model=FakeEmbeddingModel(),
        chunk_size=30,
        overlap=5,
    )

    assert result.skipped is False
    assert result.chunks_indexed > 1
    assert source.extracted_text.startswith("A procurement requires")
    assert source.content_hash == content_sha256(source.extracted_text)
    assert source.indexed_at is not None
    assert source.indexed_at.tzinfo is timezone.utc
    assert all(
        record["metadata"]["source_document_id"] == str(source.id)
        for record in collection.records.values()
    )
    assert all(
        record["metadata"]["procurement_notice_id"] == str(source.procurement_notice_id)
        for record in collection.records.values()
    )


def test_indexing_same_content_skips_reembedding(db_session):
    source = make_source(db_session)
    collection = FakeCollection()
    model = FakeEmbeddingModel()
    content = "A stable document used for duplicate indexing detection."

    first = index_source_document(
        db_session, source, content, collection=collection,
        embedding_model=model, chunk_size=100, overlap=10,
    )
    original_ids = set(collection.records)
    second = index_source_document(
        db_session, source, content, collection=collection,
        embedding_model=model, chunk_size=100, overlap=10,
    )

    assert first.chunks_indexed == 1
    assert second.skipped is True
    assert second.chunks_indexed == 0
    assert set(collection.records) == original_ids


def test_same_hash_reindexes_if_vector_records_are_missing(db_session):
    source = make_source(db_session)
    collection = FakeCollection()
    model = FakeEmbeddingModel()
    content = "Persistent content with an existing content hash."

    index_source_document(
        db_session, source, content, collection=collection,
        embedding_model=model, chunk_size=100, overlap=10,
    )
    collection.records.clear()  # Simulate a reset or lost Chroma collection.

    result = index_source_document(
        db_session, source, content, collection=collection,
        embedding_model=model, chunk_size=100, overlap=10,
    )

    assert result.skipped is False
    assert result.chunks_indexed == 1
    assert len(collection.records) == 1


def test_reindexing_shorter_content_removes_stale_chunks(db_session):
    source = make_source(db_session)
    collection = FakeCollection()
    model = FakeEmbeddingModel()
    index_source_document(
        db_session, source, "long content " * 20,
        collection=collection, embedding_model=model,
        chunk_size=30, overlap=5,
    )
    assert len(collection.records) > 1

    result = index_source_document(
        db_session, source, "Updated short content.",
        collection=collection, embedding_model=model,
        chunk_size=100, overlap=10, force=True,
    )

    assert result.chunks_indexed == 1
    assert len(collection.records) == 1
    assert next(iter(collection.records.values()))["document"] == "Updated short content."


def test_failed_embedding_does_not_mark_source_indexed(db_session):
    source = make_source(db_session)

    class BrokenModel:
        def encode(self, texts, show_progress_bar=False):
            raise RuntimeError("embedding service failed")

    with pytest.raises(RuntimeError, match="embedding service failed"):
        index_source_document(
            db_session, source, "Useful source text",
            collection=FakeCollection(), embedding_model=BrokenModel(),
        )

    assert source.indexed_at is None
    assert source.content_hash is None


def test_indexing_rejects_blank_source_text(db_session):
    source = make_source(db_session)
    with pytest.raises(ValueError, match="must not be empty"):
        index_source_document(
            db_session, source, "  ", collection=FakeCollection(),
            embedding_model=FakeEmbeddingModel(),
        )


def test_retrieve_evidence_returns_source_provenance(db_session):
    source = make_source(db_session)
    collection = FakeCollection()
    index_source_document(
        db_session, source, "Secure cloud hosting requirements.",
        collection=collection, embedding_model=FakeEmbeddingModel(),
        chunk_size=100, overlap=10,
    )

    results = retrieve_evidence(
        "cloud hosting", n_results=5, collection=collection,
        embedding_model=FakeEmbeddingModel(),
        procurement_notice_id=source.procurement_notice_id,
    )

    assert len(results) == 1
    assert results[0]["source_document_id"] == source.id
    assert results[0]["procurement_notice_id"] == source.procurement_notice_id
    assert results[0]["title"] == source.title
    assert results[0]["source_url"] == source.source_url
    assert results[0]["distance"] == 0.12
    assert collection.last_query["where"] == {
        "procurement_notice_id": str(source.procurement_notice_id)
    }


def test_retrieve_evidence_validates_query_and_limit():
    with pytest.raises(ValueError, match="cannot be empty"):
        retrieve_evidence("   ", collection=FakeCollection(), embedding_model=FakeEmbeddingModel())
    with pytest.raises(ValueError, match="between 1 and 100"):
        retrieve_evidence("question", n_results=101, collection=FakeCollection(), embedding_model=FakeEmbeddingModel())


def test_retrieve_evidence_returns_empty_when_collection_is_empty():
    assert retrieve_evidence(
        "question", collection=FakeCollection(), embedding_model=FakeEmbeddingModel()
    ) == []

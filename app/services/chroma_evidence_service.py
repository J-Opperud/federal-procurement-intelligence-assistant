"""Index source-document evidence in ChromaDB and retrieve relevant chunks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import SourceDocument,ProcurementNotice
from app.services.document_chunking import chunk_text
from app.services.document_file_service import content_sha256
from app.services.procurement_data_service import upsert_notice_source_document

@dataclass(frozen=True, slots=True)
class IndexingResult:
    """Outcome of indexing one source document."""

    chunks_indexed: int
    skipped: bool
    content_hash: str

def get_chroma_collection(collection_name: str | None = None):
    """Return Sentinel's configured persistent Chroma collection."""
    try:
        import chromadb
    except ImportError as exc:  # pragma: no cover - depends on installation
        raise RuntimeError("Vector indexing requires the 'chromadb' package.") from exc

    persist_directory = settings.chroma_persist_directory or (settings.data_dir / "chroma")
    persist_directory.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_directory))
    return client.get_or_create_collection(
        name=collection_name or settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load and cache the configured SentenceTransformer model on demand."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - depends on installation
        raise RuntimeError(
            "Embedding generation requires the 'sentence-transformers' package."
        ) from exc
    return SentenceTransformer(settings.embedding_model)


def _to_list(value: Any) -> list:
    return value.tolist() if hasattr(value, "tolist") else list(value)


def index_source_document(
    db: Session,
    source_document: SourceDocument,
    text: str | None = None,
    *,
    collection=None,
    embedding_model=None,
    chunk_size: int | None = None,
    overlap: int | None = None,
    force: bool = False,
) -> IndexingResult:
    """Persist source text and replace its indexed chunks safely.

    The text is embedded before existing vectors are changed. Stable IDs allow
    upserts to replace same-position chunks; obsolete trailing chunks are
    removed only after new chunks have been upserted successfully. Callers own
    the SQLAlchemy transaction and must commit after this function succeeds.
    """
    if source_document.id is None:
        db.flush()
    if source_document.id is None:
        raise ValueError("Source document must be persisted before indexing.")

    content = (text if text is not None else source_document.extracted_text) or ""
    content = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not content:
        raise ValueError("Source document text must not be empty.")

    digest = content_sha256(content)
    selected_chunk_size = (
        settings.document_chunk_size if chunk_size is None else chunk_size
    )
    selected_overlap = (
        settings.document_chunk_overlap if overlap is None else overlap
    )
    chunks = chunk_text(
        content,
        chunk_size=selected_chunk_size,
        overlap=selected_overlap,
    )
    if not chunks:
        raise ValueError("Source document produced no searchable chunks.")

    vector_collection = collection or get_chroma_collection()
    source_id = str(source_document.id)
    notice_id = (
        str(source_document.procurement_notice_id)
        if source_document.procurement_notice_id is not None
        else None
    )
    
    notice = (
        db.get(ProcurementNotice, source_document.procurement_notice_id)
        if source_document.procurement_notice_id is not None
        else None
    )
    
    ids = [f"source-document:{source_id}:chunk:{index}" for index in range(len(chunks))]
    existing = vector_collection.get(
        where={"source_document_id": source_id},
        include=["metadatas"],
    )
    existing_ids = set(existing.get("ids", []))
    existing_metadata = existing.get("metadatas", [])
    model_name = settings.embedding_model
    already_current = (
        source_document.content_hash == digest
        and source_document.indexed_at is not None
        and existing_ids == set(ids)
        and len(existing_metadata) == len(ids)
        and all(
            metadata.get("content_hash") == digest
            and metadata.get("embedding_model") == model_name
            and metadata.get("chunk_size") == selected_chunk_size
            and metadata.get("chunk_overlap") == selected_overlap
            for metadata in existing_metadata
        )
    )
    if not force and already_current:
        return IndexingResult(chunks_indexed=0, skipped=True, content_hash=digest)

    model = embedding_model or get_embedding_model()

    # Embed all content before mutating the vector collection.
    raw_embeddings = model.encode(chunks, show_progress_bar=False)
    embeddings = [_to_list(vector) for vector in raw_embeddings]
    if len(embeddings) != len(chunks):
        raise RuntimeError("Embedding model returned an unexpected number of vectors.")

    metadatas = []
    for index in range(len(chunks)):
        metadata = {
            "source_document_id": source_id,
            "title": source_document.title,
            "source_type": source_document.source_type,
            "chunk_index": index,
            "content_hash": digest,
            "embedding_model": model_name,
            "chunk_size": selected_chunk_size,
            "chunk_overlap": selected_overlap,
        }

        if notice_id is not None:
            metadata["procurement_notice_id"] = notice_id
        
        if source_document.source_url:
            metadata["source_url"] = source_document.source_url
            
            if notice is not None:
                metadata["sam_notice_id"] = notice.sam_notice_id
                metadata["notice_type"] = notice.notice_type

            if notice.department:
                metadata["department"] = notice.department

            if notice.posted_date is not None:
                metadata["posted_date"] = notice.posted_date.isoformat()
                metadata["posted_date_timestamp"] = (
                    notice.posted_date.timestamp()
                )

            if notice.response_deadline is not None:
                metadata["response_deadline"] = (
                    notice.response_deadline.isoformat()
                )
                metadata["response_deadline_timestamp"] = (
                    notice.response_deadline.timestamp()
                )
        metadatas.append(metadata)

    vector_collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    obsolete_ids = existing_ids.difference(ids)
    if obsolete_ids:
        vector_collection.delete(ids=sorted(obsolete_ids))

    source_document.extracted_text = content
    source_document.content_hash = digest
    source_document.indexed_at = datetime.now(timezone.utc)
    db.flush()

    return IndexingResult(
        chunks_indexed=len(chunks),
        skipped=False,
        content_hash=digest,
    )


def retrieve_evidence(
    query: str,
    *,
    n_results: int = 5,
    procurement_notice_id: int | None = None,
    source_document_id: int | None = None,
    collection=None,
    embedding_model=None,
) -> list[dict[str, Any]]:
    """Retrieve semantically relevant chunks with Sentinel provenance metadata."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Search query cannot be empty.")
    if n_results < 1 or n_results > 100:
        raise ValueError("n_results must be between 1 and 100.")

    vector_collection = collection or get_chroma_collection()
    count = vector_collection.count()
    if count == 0:
        return []

    model = embedding_model or get_embedding_model()
    query_vector = _to_list(model.encode(query.strip()))
    filters = []
    if procurement_notice_id is not None:
        filters.append({"procurement_notice_id": str(procurement_notice_id)})
    if source_document_id is not None:
        filters.append({"source_document_id": str(source_document_id)})

    kwargs = {
        "query_embeddings": [query_vector],
        "n_results": min(n_results, count),
        "include": ["documents", "metadatas", "distances"],
    }
    if len(filters) == 1:
        kwargs["where"] = filters[0]
    elif len(filters) > 1:
        kwargs["where"] = {"$and": filters}

    results = vector_collection.query(**kwargs)
    documents = (results.get("documents") or [[]])[0] or []
    metadatas = (results.get("metadatas") or [[]])[0] or []
    distances = (results.get("distances") or [[]])[0] or []

    evidence = []
    for index, document in enumerate(documents):
        metadata = metadatas[index] or {}
        evidence.append(
            {
                "text": document,
                "source_document_id": int(metadata["source_document_id"]),
                "procurement_notice_id": (
                    int(metadata["procurement_notice_id"])
                    if metadata.get("procurement_notice_id") is not None
                    else None
                ),
                "title": metadata.get("title"),
                "source_type": metadata.get("source_type"),
                "source_url": metadata.get("source_url"),
                "chunk_index": int(metadata["chunk_index"]),
                "distance": float(distances[index]),
            }
        )
    return evidence


def index_procurement_notice(db: Session, notice) -> IndexingResult:
    """Project one SQL procurement notice into ChromaDB evidence.

    The source text is committed first so an indexing failure does not lose the
    searchable projection; a later retry can re-index the saved SourceDocument.
    """
    source_document = upsert_notice_source_document(db, notice)
    db.commit()
    db.refresh(source_document)

    try:
        result = index_source_document(db, source_document)
        db.commit()
        db.refresh(source_document)
        return result
    except Exception:
        db.rollback()
        raise

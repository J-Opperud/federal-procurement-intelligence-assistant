# Project Proposal: Sentinel Scout

### Project Name and Description

**Sentinel Scout — Federal Procurement Intelligence Assistant**

Sentinel Scout is an AI-powered procurement research application that retrieves federal acquisition information from SAM.gov and uses retrieval-augmented generation (RAG) to answer questions with traceable evidence from official government documents.

### User Story

As a federal procurement researcher, I want to search procurement notices and ask questions about acquisition opportunities so that I can identify relevant information quickly and verify answers against authoritative government sources.

### Required Components Checklist

- [ ] **FastAPI backend:** Provide at least three endpoints: `POST /auth/token` for user authentication, `GET /documents` for procurement document discovery, and `POST /ask` for RAG-powered question answering. Additional endpoints will support ingestion and health checks.
- [ ] **SQLAlchemy database:** Use SQLite with related `Users` and `ResearchQueries` tables, linked by a foreign key, and procurement notice records to support document tracking.
- [ ] **Pydantic validation:** Validate request and response data across all API endpoints, including authentication, search parameters, and research questions.
- [ ] **JWT authentication:** Issue and validate application access tokens using a securely stored signing secret.
- [ ] **RAG pipeline:** Use ChromaDB for vector storage and retrieval, with Ollama for local LLM answer generation. Return relevant source passages with answers.
- [ ] **Streamlit frontend:** Provide a user interface for authentication, procurement search, question answering, and source inspection.
- [ ] **Docker Compose:** Containerize the application services so the complete stack can be started with one documented command.
- [ ] **Automated tests:** Write and pass at least five tests covering API behavior, validation, authentication, database relationships, and retrieval.
- [ ] **README:** Document installation, configuration, architecture, usage, and known limitations.
- [ ] **Dependencies:** Include `requirements.txt` or per-service dependency files.

### Data Sources

The primary structured data source will be the official **SAM.gov Contract Opportunities Public API**, using an API key stored in an environment variable. Procurement notices will be validated and stored as structured records.

The initial RAG corpus will include official Federal Acquisition Regulation (FAR) documents, focusing on Parts 2 (definitions), 7 (acquisition planning), 9 (contractor qualifications), 10 (market research), and 19 (small business programs). Retrieved notice descriptions and relevant document passages will provide additional context for procurement research.

### Technology Stack

Python, FastAPI, SQLAlchemy, SQLite, Pydantic, JWT, ChromaDB, Ollama, Streamlit, Docker, and Docker Compose. Environment variables managed through `.env` will keep the SAM.gov API key and JWT signing secret out of source code.

### Project Risks and Mitigation

**Risk 1 — API access or rate limits:** SAM.gov access, request limits, or service availability may interrupt data collection.
**Mitigation:** Use the documented API, respect its limits, implement timeouts and error handling, and retain a small set of previously retrieved or official sample notices for offline demonstrations.

**Risk 2 — Retrieval quality or unsupported answers:** The RAG pipeline may retrieve irrelevant passages or generate answers unsupported by the source documents.
**Mitigation:** Evaluate retrieval against a labeled question set, display source passages and identifiers, and provide an insufficient-evidence response when the available context does not support an answer.

### Success Criteria

Deliver a working, containerized procurement research application that authenticates users, retrieves official procurement information, answers questions with traceable source evidence, passes automated tests, and can be configured and demonstrated using the README instructions.

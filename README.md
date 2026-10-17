
# Sentinel Scout

AI-powered federal procurement intelligence assistant using retrieval-augmented generation (RAG).

## System Architecture

The diagram below shows the application's services, communication paths, and data storage.

```mermaid
flowchart TB
    USER["Researcher / User<br/>Search notices and ask questions"]

    subgraph DOCKER["Docker Compose Network"]
        UI["Streamlit Frontend<br/>Port 8501"]
        API["FastAPI Backend<br/>JWT Auth · Pydantic · RAG"]
        DB[("SQLite Database<br/>Users · Notices · Sources · Queries")]
        CHROMA[("ChromaDB<br/>Embeddings · Vector Search")]
        OLLAMA["Ollama<br/>Local LLM Inference"]

        UI <-->|"HTTP / JSON"| API
        API <-->|"SQLAlchemy"| DB
        API -->|"Query vectors"| CHROMA
        CHROMA -->|"Retrieved context"| API
        API -->|"Prompt + context"| OLLAMA
        OLLAMA -->|"Generated answer"| API
    end

    SAM["SAM.gov Public API<br/>Official procurement notices"]

    USER <-->|"Browser · HTTP"| UI
    API -->|"HTTPS + API key"| SAM
    SAM -->|"Notice JSON"| API

    VOL[("Docker Volumes<br/>Persistent storage")]
    DB --- VOL
    CHROMA --- VOL
    OLLAMA --- VOL
```

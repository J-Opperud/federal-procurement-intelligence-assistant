
import httpx
import pytest

from app.services.ollama_client import OllamaError, generate_answer


@pytest.fixture
def evidence():
    return [
        {
            "source_document_id": 12,
            "chunk_index": 0,
            "title": "Procurement Notice",
            "source_url": "https://example.com/notice",
            "text": "The agency issued a sources-sought notice.",
            "distance": 0.15,
        }
    ]


def mock_ollama_client(monkeypatch, answer, captured_dict=None):
    """Helper to mock httpx.Client context manager for ollama_client service."""
    class MockResponse:
        def status_code(self):
            return 200

        def json(self):
            return {"message": {"content": answer}}

        def raise_for_status(self):
            pass

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def post(self, url, *, json=None, **kwargs):
            if captured_dict is not None:
                captured_dict["payload"] = json
            return httpx.Response(
                200,
                json={"message": {"content": answer}},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr("app.services.ollama_client.httpx.Client", MockClient)


def test_generate_answer_uses_source_labels(monkeypatch, evidence):
    mock_ollama_client(monkeypatch, "The agency issued a notice [Source 1].")

    answer = generate_answer("What did the agency issue?", evidence)

    assert answer == "The agency issued a notice [Source 1]."


def test_generate_answer_prompt_uses_descriptive_labels(monkeypatch, evidence):
    captured = {}
    mock_ollama_client(monkeypatch, "The agency issued a notice [Source 1].", captured_dict=captured)

    generate_answer("What did the agency issue?", evidence)

    prompt = captured["payload"]["messages"][1]["content"]
    assert "[Source 1] Procurement Notice" in prompt
    assert "[S1]" not in prompt


def test_generate_answer_rejects_nonexistent_source(monkeypatch, evidence):
    mock_ollama_client(monkeypatch, "The agency issued a notice [Source 2].")

    with pytest.raises(OllamaError, match="(?i)citation"):
        generate_answer("What did the agency issue?", evidence)


def test_generate_answer_rejects_answer_without_citation(monkeypatch, evidence):
    mock_ollama_client(monkeypatch, "The agency issued a notice.")

    with pytest.raises(OllamaError, match="(?i)without citing|citation"):
        generate_answer("What did the agency issue?", evidence)


def test_generate_answer_wraps_http_errors(monkeypatch, evidence):
    class MockErrorClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def post(self, url, *, json=None, **kwargs):
            raise httpx.ConnectError("Ollama unavailable", request=httpx.Request("POST", url))

    monkeypatch.setattr("app.services.ollama_client.httpx.Client", MockErrorClient)

    with pytest.raises(OllamaError, match="(?i)request failed|unavailable|error"):
        generate_answer("What did the agency issue?", evidence)
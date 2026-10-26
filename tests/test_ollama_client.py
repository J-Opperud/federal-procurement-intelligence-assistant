
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


def mock_ollama(monkeypatch, answer):
    def fake_post(*args, **kwargs):
        return httpx.Response(
            200,
            json={"message": {"content": answer}},
            request=httpx.Request("POST", "http://test/api/chat"),
        )

    monkeypatch.setattr("app.services.ollama_client.httpx.post", fake_post)


def test_generate_answer_uses_source_labels(monkeypatch, evidence):
    mock_ollama(monkeypatch, "The agency issued a notice [Source 1].")

    answer = generate_answer("What did the agency issue?", evidence)

    assert answer == "The agency issued a notice [Source 1]."


def test_generate_answer_prompt_uses_descriptive_labels(monkeypatch, evidence):
    captured = {}

    def fake_post(url, *, json, timeout):
        captured["payload"] = json
        return httpx.Response(
            200,
            json={"message": {"content": "The agency issued a notice [Source 1]."}},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr("app.services.ollama_client.httpx.post", fake_post)

    generate_answer("What did the agency issue?", evidence)

    prompt = captured["payload"]["messages"][1]["content"]
    assert "[Source 1] Procurement Notice" in prompt
    assert "[S1]" not in prompt


def test_generate_answer_rejects_nonexistent_source(monkeypatch, evidence):
    mock_ollama(monkeypatch, "The agency issued a notice [Source 2].")

    with pytest.raises(OllamaError, match="citation"):
        generate_answer("What did the agency issue?", evidence)


def test_generate_answer_rejects_answer_without_citation(monkeypatch, evidence):
    mock_ollama(monkeypatch, "The agency issued a notice.")

    with pytest.raises(OllamaError, match="without citing"):
        generate_answer("What did the agency issue?", evidence)


def test_generate_answer_wraps_http_errors(monkeypatch, evidence):
    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("Ollama unavailable")

    monkeypatch.setattr("app.services.ollama_client.httpx.post", fake_post)

    with pytest.raises(OllamaError, match="request failed"):
        generate_answer("What did the agency issue?", evidence)

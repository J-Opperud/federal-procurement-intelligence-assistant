"""Small HTTP client for local Ollama chat completion."""

import re
from typing import Any

import httpx

from app.config import settings


class OllamaError(RuntimeError):
    """Raised when Ollama cannot return a usable answer."""


# 1. Cleaner, punchier rules optimized for local chat models
SYSTEM_PROMPT = """You are Scout, a federal procurement research assistant. 

CRITICAL CITATION RULE:
Every single factual statement, title, date, or detail you provide MUST end with its exact source tag in square brackets (e.g., [Source 1]). If you do not include a source tag like [Source 1] at the end of your sentences, your answer will be rejected.

CORE RULES:
1. GROUNDING: Answer strictly using the supplied retrieved evidence. Never assume or invent facts.
2. UNKNOWN DATA: If the evidence does not contain the answer, explicitly state what is missing.
3. STYLE: Be direct, concise, and professional."""


def generate_answer(question: str, evidence: list[dict[str, Any]]) -> str:
    """Generate a grounded answer using only the supplied retrieved passages."""

    passages = []
    for index, item in enumerate(evidence, start=1):
        title = item.get("title") or "Untitled source"
        url = item.get("source_url") or "URL unavailable"
        passages.append(
            f"[Source {index}] {title} | {url} | "
            f"source_document_id={item.get('source_document_id')} | "
            f"chunk_index={item.get('chunk_index')}\n"
            f"{item.get('text', '')}"
        )

    context = "\n\n".join(passages)

    # 2. Keep the user prompt clean and focused strictly on the question and data
    user_prompt = (
        f"Question:\n{question}\n\n"
        f"Retrieved Evidence:\n{context}\n\n"
        "Provide a concise, cited answer based only on this evidence."
    )

    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"

    timeout_config = httpx.Timeout(
        connect=10.0,
        read=settings.ollama_timeout_seconds,
        write=30.0,
        pool=10.0
    )

    try:
        with httpx.Client(timeout=timeout_config) as client:
            response = client.post(
                url,
                json={
                    "model": settings.ollama_model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "options": {"temperature": 0},
                },
            )
            response.raise_for_status()
            payload = response.json()

    except httpx.TimeoutException as exc:
        raise OllamaError(
            f"Ollama request timed out after {timeout_config.read} seconds."
        ) from exc
    except httpx.HTTPError as exc:
        raise OllamaError(f"Ollama HTTP communication failed: {exc}") from exc
    except ValueError as exc:
        raise OllamaError("Ollama returned malformed JSON response.") from exc

    if not isinstance(payload, dict):
        raise OllamaError("Ollama returned an invalid response shape.")

    message = payload.get("message")
    answer = message.get("content") if isinstance(message, dict) else None

    if not isinstance(answer, str) or not answer.strip():
        raise OllamaError("Ollama returned an empty answer.")

    # Validate citations
    citation_numbers = [
        int(value)
        for value in re.findall(r"\[Source ([1-9]\d*)\]", answer)
    ]

    if not citation_numbers:
        raise OllamaError(
            "Ollama returned an answer without citing retrieved evidence."
        )

    if any(number < 1 or number > len(evidence) for number in citation_numbers):
        raise OllamaError(
            "Ollama returned a citation that was not in the retrieved evidence."
        )

    return answer.strip()
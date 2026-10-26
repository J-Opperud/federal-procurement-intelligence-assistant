"""Read and normalize local TXT, Markdown, and PDF source files."""

from __future__ import annotations

import hashlib
from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

def content_sha256(text: str) -> str:
    """Return a stable SHA-256 digest for normalized extracted text."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def extract_document_text(path: Path) -> str:
    """Extract text from a supported local file without silently ignoring errors."""
    if not path.is_file():
        raise FileNotFoundError(f"Source document does not exist: {path}")

    extension = path.suffix.lower()
    if extension in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8")
    elif extension == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - depends on installation
            raise RuntimeError("PDF extraction requires the 'pypdf' package.") from exc
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        raise ValueError(f"Unsupported source document type: {extension or '[none]'}")

    text = text.strip()
    if not text:
        raise ValueError(f"No extractable text found in source document: {path.name}")
    return text



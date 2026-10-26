"""Text chunking adapted from the semantic_search_tool repository."""


def chunk_text(
    text: str,
    chunk_size: int = 300,
    overlap: int = 50,
) -> list[str]:
    """Split text into overlapping, non-empty character chunks.

    This deliberately preserves the source tool's simple character-based
    strategy so the capstone can reuse its tested behavior without coupling
    Sentinel to the standalone Streamlit application.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    if overlap < 0:
        raise ValueError("overlap cannot be negative.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    text = text.strip()
    if not text:
        return []

    step = chunk_size - overlap
    chunks = []
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        
        if start + chunk_size >= len(text):
            break
    return chunks
